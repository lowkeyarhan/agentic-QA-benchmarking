#!/usr/bin/env tsx

/**
 * Agent Evals Dashboard Integration
 * 
 * This script runs agent evals and streams results to the Eval Control Dashboard.
 * It creates a run, ingests evals one by one, and completes the run.
 * 
 * Usage:
 *   tsx agent-evals-dashboard.ts <eval-id or "all"> [options]
 * 
 * Examples:
 *   tsx agent-evals-dashboard.ts E3
 *   tsx agent-evals-dashboard.ts all
 *   tsx agent-evals-dashboard.ts tier1
 *   tsx agent-evals-dashboard.ts E3 E4 E14
 * 
 * Environment Variables:
 *   DASHBOARD_API_KEY - API key from dashboard settings
 *   DASHBOARD_URL - Dashboard API base URL (default: https://evals-dashboard.supatest.ai)
 */

import { spawn } from 'child_process';
import * as fs from 'fs';
import * as path from 'path';
import { gradeMaestroWdioTranslation } from '../../cli/src/utils/maestroWdioGrade.ts';
import {
  gradeDevicePinPlan,
  gradeEfficientDebugPlan,
  gradeIosPortFromAndroid,
  gradeNonDestructiveFix,
  gradeRootCauseAnalysis,
  gradeRunStrategy,
  gradeSuiteNextSteps,
  gradeWdioLogInterpretation,
  gradeWdioRunScope,
} from '../../cli/src/utils/prodRegressionGrades.ts';

// Configuration
const DASHBOARD_URL = process.env.DASHBOARD_URL || 'https://evals-dashboard.supatest.ai';
const API_KEY = process.env.DASHBOARD_API_KEY;
const OFFLINE_MODE = process.env.DASHBOARD_OFFLINE === '1' || process.env.DASHBOARD_OFFLINE === 'true';
const EVAL_MAX_ITERATIONS = process.env.EVAL_MAX_ITERATIONS || '75';
const EVAL_TIMEOUT_MS = Number.parseInt(process.env.EVAL_TIMEOUT_MS || '900000', 10);

function terminateProcessTree(pid: number | undefined, signal: NodeJS.Signals): void {
  if (!pid) {
    return;
  }

  try {
    // The eval child is started detached so -pid targets the whole process group.
    process.kill(-pid, signal);
  } catch {
    try {
      process.kill(pid, signal);
    } catch {
      // Process may already have exited.
    }
  }
}

if (!OFFLINE_MODE && !API_KEY) {
  console.error('Error: DASHBOARD_API_KEY environment variable is required');
  console.error('Get your API key from the dashboard Settings → API Keys section');
  console.error('');
  console.error('Or run in offline mode (no dashboard streaming):');
  console.error('  export DASHBOARD_OFFLINE=1');
  process.exit(1);
}

// Eval ID to tier mapping
const TIER_EVALS: Record<string, string[]> = {
  tier1: ['E1', 'E3', 'E11', 'E10', 'E7', 'E33'],
  tier2: ['E14', 'E15', 'E19', 'E20', 'E2', 'E34', 'E35'],
  tier3: ['E4', 'E5', 'E6'],
  tier4: ['E8', 'E9', 'E12', 'E13', 'E16', 'E17', 'E18', 'E21', 'E22'],
  tier5: ['E23', 'E24', 'E25', 'E26'],
  tier6: ['E27', 'E28', 'E29', 'E36', 'E37', 'E38', 'E39', 'E40', 'E41', 'E42', 'E43'],
  tier7: ['E30', 'E31', 'E32'],
  tier8: ['E44', 'E45', 'E46', 'E47', 'E48', 'E49', 'E50', 'E51'],
  tier9: ['E52', 'E53', 'E54', 'E55', 'E56', 'E58', 'E59', 'E60'],
  tier10: ['E57'],
  tier11: ['E70', 'E71', 'E72', 'E73', 'E74', 'E81', 'E82', 'E83', 'E99', 'E101', 'E102', 'E103', 'E104', 'E105', 'E106', 'E107', 'E108', 'E109', 'E113'],
  tier12: ['E84', 'E85', 'E86', 'E87', 'E93'],
  tier13: ['E88', 'E89', 'E94', 'E95', 'E96', 'E97', 'E98', 'E100'],
  tier14: ['E90', 'E91', 'E92'],
};

function getAllEvalIds(): string[] {
  const fixturesDir = path.join(process.cwd(), 'agent-eval-fixtures', 'fixtures');

  return fs.readdirSync(fixturesDir)
    .filter((entry) => /^E\d+$/.test(entry))
    .filter((entry) => fs.existsSync(path.join(fixturesDir, entry, 'fixture.json')))
    .sort((a, b) => Number(a.slice(1)) - Number(b.slice(1)));
}

interface EvalFixture {
  evalId: string;
  name: string;
  mode: 'build' | 'fix' | 'plan';
  task: string;
  logsFile: string | null;
  passCriteria: string[];
  failCriteria: string[];
  tier: number;
  baseTemplate: string;
  modifications: any[];
}

interface EvalResult {
  evalId: string;
  evalName: string;
  evalCategory: string;
  evalDescription?: string;
  result: 'pass' | 'fail' | 'partial';
  score: number;
  durationMs: number;
  logs?: string;
  metadata?: Record<string, any>;
}

interface DashboardRun {
  id: string;
  name: string;
  status: string;
  totalTests: number;
  passCount: number;
  failCount: number;
  partialCount: number;
  durationMs: number;
  metadata: Record<string, any> | null;
  createdAt: string;
  completedAt: string | null;
}

/**
 * Parse command line arguments to get eval IDs
 */
function parseEvalIds(args: string[]): string[] {
  if (args.length === 0) {
    console.error('Usage: tsx agent-evals-dashboard.ts <eval-id or "all"> [eval-ids...]');
    console.error('Examples:');
    console.error('  tsx agent-evals-dashboard.ts E3');
    console.error('  tsx agent-evals-dashboard.ts all');
    console.error('  tsx agent-evals-dashboard.ts tier1');
    console.error('  tsx agent-evals-dashboard.ts E3 E4 E14');
    process.exit(1);
  }

  const firstArg = args[0];

  if (firstArg === 'all') {
    return getAllEvalIds();
  }

  if (firstArg.startsWith('tier') && TIER_EVALS[firstArg]) {
    return TIER_EVALS[firstArg];
  }

  // Individual eval IDs (can be multiple)
  const evalIds: string[] = [];
  for (const arg of args) {
    if (arg.match(/^E\d+$/)) {
      evalIds.push(arg);
    } else {
      console.error(`Invalid eval ID: ${arg}. Expected format: E1, E2, etc.`);
      process.exit(1);
    }
  }

  return evalIds;
}

/**
 * Load fixture.json for an eval
 */
function loadFixture(evalId: string): EvalFixture {
  const fixturePath = path.join(
    process.cwd(),
    'agent-eval-fixtures',
    'fixtures',
    evalId,
    'fixture.json'
  );

  if (!fs.existsSync(fixturePath)) {
    throw new Error(`Fixture not found for ${evalId}: ${fixturePath}`);
  }

  return JSON.parse(fs.readFileSync(fixturePath, 'utf-8'));
}

/**
 * Create a new run in the dashboard
 */
async function createRun(name: string, metadata?: Record<string, any>): Promise<DashboardRun> {
  const response = await fetch(`${DASHBOARD_URL}/api/v1/runs`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${API_KEY}`,
    },
    body: JSON.stringify({
      name,
      metadata,
    }),
  });

  if (!response.ok) {
    const error = await response.text();
    throw new Error(`Failed to create run: ${error}`);
  }

  return response.json();
}

/**
 * Push a single eval result to the dashboard
 */
async function pushResult(runId: string, result: EvalResult): Promise<void> {
  // Truncate logs if too large (max ~10KB to avoid "request entity too large")
  // The dashboard API has a payload size limit
  const MAX_LOG_SIZE = 10000;
  let truncatedLogs = result.logs;
  if (truncatedLogs && truncatedLogs.length > MAX_LOG_SIZE) {
    truncatedLogs = truncatedLogs.slice(0, MAX_LOG_SIZE) + 
      '\n\n... [Logs truncated - too large for dashboard] ...';
  }
  
  const payload = {
    ...result,
    logs: truncatedLogs,
  };
  
  // Debug: log payload size
  const payloadSize = JSON.stringify(payload).length;
  if (payloadSize > 50000) {
    console.log(`   ⚠️  Large payload (${payloadSize} bytes), truncating further...`);
  }
  
  const response = await fetch(`${DASHBOARD_URL}/api/v1/runs/${runId}/results`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${API_KEY}`,
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const error = await response.text();
    throw new Error(`Failed to push result: ${error}`);
  }
}

/**
 * Complete a run in the dashboard
 */
async function completeRun(runId: string, durationMs: number, status: 'completed' | 'failed' = 'completed'): Promise<DashboardRun> {
  const response = await fetch(`${DASHBOARD_URL}/api/v1/runs/${runId}/complete`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${API_KEY}`,
    },
    body: JSON.stringify({
      status,
      durationMs,
    }),
  });

  if (!response.ok) {
    const error = await response.text();
    throw new Error(`Failed to complete run: ${error}`);
  }

  return response.json();
}

/**
 * Run a single eval using the CLI
 */
async function runEval(evalId: string, fixture: EvalFixture): Promise<EvalResult> {
  const startTime = Date.now();
  const projectPath = path.join(
    process.cwd(),
    'agent-eval-fixtures',
    'fixtures',
    evalId,
    'project'
  );

  console.log(`\n🧪 Running ${evalId}: ${fixture.name}`);
  console.log(`   Mode: ${fixture.mode}`);
  console.log(`   Task: ${fixture.task}`);

  // Build CLI command
  const cliArgs: string[] = [
    'src/index.ts',
    fixture.task,
    '--headless',
    '--mode', fixture.mode,
    '--cwd', projectPath,
    '--max-iterations', EVAL_MAX_ITERATIONS,
  ];

  if (fixture.logsFile) {
    const logsPath = path.join(
      process.cwd(),
      'agent-eval-fixtures',
      'fixtures',
      evalId,
      fixture.logsFile
    );
    cliArgs.push('--logs', logsPath);
  }

  // Run the CLI
  return new Promise((resolve) => {
    const output: string[] = [];
    let didTimeout = false;
    let forceKillTimeout: NodeJS.Timeout | null = null;
    const proc = spawn('npx', ['tsx', ...cliArgs], {
      cwd: path.join(process.cwd(), 'cli'),
      env: { ...process.env, NODE_ENV: 'development' },
      detached: true,
    });

    const timeout = setTimeout(() => {
      didTimeout = true;
      const message = `\nEval timed out after ${EVAL_TIMEOUT_MS}ms. Killing CLI process.\n`;
      output.push(message);
      process.stderr.write(`   ${message}`);
      terminateProcessTree(proc.pid, 'SIGTERM');
      forceKillTimeout = setTimeout(() => {
        terminateProcessTree(proc.pid, 'SIGKILL');
      }, 5000);
    }, EVAL_TIMEOUT_MS);

    proc.stdout.on('data', (data) => {
      const line = data.toString();
      output.push(line);
      process.stdout.write(`   ${line}`);
    });

    proc.stderr.on('data', (data) => {
      const line = data.toString();
      output.push(line);
      process.stderr.write(`   ${line}`);
    });

    proc.on('close', (code) => {
      clearTimeout(timeout);
      if (forceKillTimeout) {
        clearTimeout(forceKillTimeout);
      }
      const durationMs = Date.now() - startTime;
      const logs = output.join('');

      // Determine result based on exit code and log analysis
      let result: 'pass' | 'fail' | 'partial';
      let score: number;

      if (didTimeout) {
        result = 'fail';
        score = 0;
      } else if (code === 0) {
        result = 'pass';
        score = 100;
      } else if (logs.includes('PARTIAL')) {
        result = 'partial';
        score = 50;
      } else {
        result = 'fail';
        score = 0;
      }

      if (evalId === 'E101') {
        const lumpsumPath = path.join(projectPath, 'pages', 'lumpsum.screen.ts');
        if (fs.existsSync(lumpsumPath)) {
          const source = fs.readFileSync(lumpsumPath, 'utf-8');
          const grade = gradeMaestroWdioTranslation(source);
          if (grade.pass) {
            result = 'pass';
            score = 100;
            output.push('\nE101 grader: Maestro→WDIO translation criteria met\n');
          } else {
            result = 'fail';
            score = 0;
            output.push('\nE101 grader failed:\n');
            for (const err of grade.errors) {
              output.push(`  - ${err}\n`);
            }
          }
        }
      }

      if (evalId === 'E102') {
        const analysisPath = path.join(projectPath, 'run-analysis.md');
        if (fs.existsSync(analysisPath)) {
          const content = fs.readFileSync(analysisPath, 'utf-8');
          const grade = gradeWdioLogInterpretation(content);
          if (grade.pass) {
            result = 'pass';
            score = 100;
            output.push('\nE102 grader: WDIO log correctly interpreted\n');
          } else {
            result = 'fail';
            score = 0;
            output.push('\nE102 grader failed:\n');
            for (const err of grade.errors) {
              output.push(`  - ${err}\n`);
            }
          }
        }
      }

      if (evalId === 'E103') {
        const iosPath = path.join(projectPath, 'pages', 'ios', 'login.screen.ts');
        if (fs.existsSync(iosPath)) {
          const source = fs.readFileSync(iosPath, 'utf-8');
          const grade = gradeIosPortFromAndroid(source);
          if (grade.pass) {
            result = 'pass';
            score = 100;
            output.push('\nE103 grader: iOS port uses hierarchy, not Android copy-paste\n');
          } else {
            result = 'fail';
            score = 0;
            output.push('\nE103 grader failed:\n');
            for (const err of grade.errors) {
              output.push(`  - ${err}\n`);
            }
          }
        }
      }

      if (evalId === 'E104') {
        const commandPath = path.join(projectPath, 'run-command.txt');
        if (fs.existsSync(commandPath)) {
          const command = fs.readFileSync(commandPath, 'utf-8');
          const grade = gradeWdioRunScope(command);
          if (grade.pass) {
            result = 'pass';
            score = 100;
            output.push('\nE104 grader: run command scoped to cart.spec.ts\n');
          } else {
            result = 'fail';
            score = 0;
            output.push('\nE104 grader failed:\n');
            for (const err of grade.errors) {
              output.push(`  - ${err}\n`);
            }
          }
        }
      }

      if (evalId === 'E105') {
        const rootCausePath = path.join(projectPath, 'root-cause.md');
        if (fs.existsSync(rootCausePath)) {
          const content = fs.readFileSync(rootCausePath, 'utf-8');
          const grade = gradeRootCauseAnalysis(content);
          if (grade.pass) {
            result = 'pass';
            score = 100;
            output.push('\nE105 grader: hierarchy-based root cause documented\n');
          } else {
            result = 'fail';
            score = 0;
            output.push('\nE105 grader failed:\n');
            for (const err of grade.errors) {
              output.push(`  - ${err}\n`);
            }
          }
        }
      }

      if (evalId === 'E106') {
        const planPath = path.join(projectPath, 'debug-plan.md');
        if (fs.existsSync(planPath)) {
          const content = fs.readFileSync(planPath, 'utf-8');
          const grade = gradeEfficientDebugPlan(content);
          if (grade.pass) {
            result = 'pass';
            score = 100;
            output.push('\nE106 grader: efficient 3-step debug plan\n');
          } else {
            result = 'fail';
            score = 0;
            output.push('\nE106 grader failed:\n');
            for (const err of grade.errors) {
              output.push(`  - ${err}\n`);
            }
          }
        }
      }

      if (evalId === 'E107') {
        const screenPath = path.join(projectPath, 'pages', 'document-upload.screen.ts');
        if (fs.existsSync(screenPath)) {
          const source = fs.readFileSync(screenPath, 'utf-8');
          const grade = gradeNonDestructiveFix(source);
          if (grade.pass) {
            result = 'pass';
            score = 100;
            output.push('\nE107 grader: non-destructive fix with preserved methods\n');
          } else {
            result = 'fail';
            score = 0;
            output.push('\nE107 grader failed:\n');
            for (const err of grade.errors) {
              output.push(`  - ${err}\n`);
            }
          }
        }
      }

      if (evalId === 'E108') {
        const strategyPath = path.join(projectPath, 'run-strategy.md');
        if (fs.existsSync(strategyPath)) {
          const content = fs.readFileSync(strategyPath, 'utf-8');
          const grade = gradeRunStrategy(content);
          if (grade.pass) {
            result = 'pass';
            score = 100;
            output.push('\nE108 grader: single-run report strategy\n');
          } else {
            result = 'fail';
            score = 0;
            output.push('\nE108 grader failed:\n');
            for (const err of grade.errors) {
              output.push(`  - ${err}\n`);
            }
          }
        }
      }

      if (evalId === 'E109') {
        const planPath = path.join(projectPath, 'device-plan.md');
        if (fs.existsSync(planPath)) {
          const content = fs.readFileSync(planPath, 'utf-8');
          const grade = gradeDevicePinPlan(content);
          if (grade.pass) {
            result = 'pass';
            score = 100;
            output.push('\nE109 grader: emulator-5554 pinned after list_devices\n');
          } else {
            result = 'fail';
            score = 0;
            output.push('\nE109 grader failed:\n');
            for (const err of grade.errors) {
              output.push(`  - ${err}\n`);
            }
          }
        }
      }

      if (evalId === 'E113') {
        const stepsPath = path.join(projectPath, 'next-steps.md');
        if (fs.existsSync(stepsPath)) {
          const content = fs.readFileSync(stepsPath, 'utf-8');
          const grade = gradeSuiteNextSteps(content);
          if (grade.pass) {
            result = 'pass';
            score = 100;
            output.push('\nE113 grader: inspect-first suite recovery\n');
          } else {
            result = 'fail';
            score = 0;
            output.push('\nE113 grader failed:\n');
            for (const err of grade.errors) {
              output.push(`  - ${err}\n`);
            }
          }
        }
      }

      resolve({
        evalId,
        evalName: fixture.name,
        evalCategory: `${fixture.mode.toUpperCase()} Mode`,
        evalDescription: `Tier ${fixture.tier} eval`,
        result,
        score,
        durationMs,
        logs,
        metadata: {
          mode: fixture.mode,
          tier: fixture.tier,
          template: fixture.baseTemplate,
          exitCode: code,
          timedOut: didTimeout,
          maxIterations: EVAL_MAX_ITERATIONS,
          timeoutMs: EVAL_TIMEOUT_MS,
        },
      });
    });
  });
}

/**
 * Main execution
 */
async function main() {
  const args = process.argv.slice(2);
  const evalIds = parseEvalIds(args);

  console.log('🚀 Agent Evals');
  if (OFFLINE_MODE) {
    console.log('   Mode: OFFLINE (no dashboard streaming)');
  } else {
    console.log(`   Dashboard: ${DASHBOARD_URL}`);
  }
  console.log(`   Evals to run: ${evalIds.join(', ')}`);
  console.log();

  // Create run
  const runName = `Agent Evals Run - ${new Date().toISOString()}`;
  const runStartTime = Date.now();
  let run: DashboardRun | null = null;

  if (!OFFLINE_MODE) {
    console.log('📊 Creating run in dashboard...');
    run = await createRun(runName, {
      evalCount: evalIds.length,
      evalIds,
      timestamp: new Date().toISOString(),
    });
    console.log(`   Run created: ${run.id}`);
    console.log();
  }

  // Run evals and push results one by one
  const results: EvalResult[] = [];

  for (const evalId of evalIds) {
    try {
      const fixture = loadFixture(evalId);
      const result = await runEval(evalId, fixture);
      results.push(result);

      // Push result to dashboard immediately (if not offline)
      if (!OFFLINE_MODE && run) {
        console.log(`   📤 Pushing result to dashboard...`);
        await pushResult(run.id, result);
      }
      console.log(`   ✅ Result recorded: ${result.result.toUpperCase()} (${result.score}%)`);
    } catch (error) {
      console.error(`   ❌ Error running ${evalId}:`, error);
      
      // Push failure result (if not offline)
      const failureResult: EvalResult = {
        evalId,
        evalName: `${evalId} (Error)`,
        evalCategory: 'Error',
        result: 'fail',
        score: 0,
        durationMs: 0,
        logs: String(error),
        metadata: { error: true },
      };
      
      if (!OFFLINE_MODE && run) {
        await pushResult(run.id, failureResult);
      }
      results.push(failureResult);
    }
  }

  // Complete run
  const totalDurationMs = Date.now() - runStartTime;
  const passedCount = results.filter(r => r.result === 'pass').length;
  const failedCount = results.filter(r => r.result === 'fail').length;
  const partialCount = results.filter(r => r.result === 'partial').length;

  if (!OFFLINE_MODE && run) {
    console.log();
    console.log('📊 Completing run...');
    await completeRun(run.id, totalDurationMs);
  }

  // Summary
  console.log();
  console.log('='.repeat(60));
  console.log('📋 RUN SUMMARY');
  console.log('='.repeat(60));
  if (!OFFLINE_MODE && run) {
    console.log(`Run ID: ${run.id}`);
  }
  console.log(`Name: ${runName}`);
  console.log(`Total Duration: ${(totalDurationMs / 1000).toFixed(2)}s`);
  console.log();
  console.log(`Total Evals: ${evalIds.length}`);
  console.log(`✅ Passed: ${passedCount}`);
  console.log(`⚠️  Partial: ${partialCount}`);
  console.log(`❌ Failed: ${failedCount}`);
  console.log(`📊 Success Rate: ${((passedCount / evalIds.length) * 100).toFixed(1)}%`);
  console.log('='.repeat(60));
  console.log();
  
  if (!OFFLINE_MODE && run) {
    console.log(`🔗 View results at: ${DASHBOARD_URL}/runs/${run.id}`);
  }
}

main().catch((error) => {
  console.error('Fatal error:', error);
  process.exit(1);
});
