import { exec } from 'child_process';
import * as fs from 'fs/promises';
import * as path from 'path';
import { promisify } from 'util';

const execAsync = promisify(exec);

const FIX_MODE_EVALS = ['E14', 'E15', 'E16', 'E27', 'E28', 'E29'];

async function captureFailureLog(evalId: string) {
  const baseDir = path.join(__dirname, '..');
  const fixtureDir = path.join(baseDir, 'fixtures', evalId);
  const projectDir = path.join(fixtureDir, 'project');
  const logFile = path.join(fixtureDir, 'failure.log');

  console.log(`Capturing failure log for ${evalId}...`);

  // 1. Install dependencies
  console.log(`  Installing dependencies...`);
  await execAsync('npm install', { cwd: projectDir });

  // 2. Run tests and capture output (expect failure)
  console.log(`  Running tests...`);
  try {
    const { stdout, stderr } = await execAsync(
      'npx playwright test --reporter=list',
      { cwd: projectDir }
    );
    // Tests passed unexpectedly
    console.log(`  WARNING: Tests passed! Fixture may not have broken code.`);
    await fs.writeFile(logFile, stdout + '\n' + stderr);
  } catch (error: any) {
    // Tests failed as expected
    const output = (error.stdout || '') + '\n' + (error.stderr || '');
    await fs.writeFile(logFile, output);
    console.log(`  Captured failure log (${output.length} bytes)`);
  }
}

async function main() {
  const evalId = process.argv[2];

  if (evalId) {
    // Run for specific eval
    if (!FIX_MODE_EVALS.includes(evalId)) {
      console.error(`${evalId} is not a fix-mode eval`);
      process.exit(1);
    }
    await captureFailureLog(evalId);
  } else {
    // Run for all fix-mode evals
    for (const id of FIX_MODE_EVALS) {
      await captureFailureLog(id);
    }
  }
}

main().catch(console.error);
