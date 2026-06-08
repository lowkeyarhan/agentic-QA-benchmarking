import * as fs from 'fs/promises';
import * as path from 'path';

interface ValidationResult {
  evalId: string;
  valid: boolean;
  errors: string[];
}

async function validateFixture(evalId: string, baseDir: string): Promise<ValidationResult> {
  const errors: string[] = [];
  const fixtureDir = path.join(baseDir, 'fixtures', evalId);

  try {
    await fs.access(fixtureDir);
  } catch {
    return { evalId, valid: false, errors: ['Fixture directory does not exist'] };
  }

  const fixtureJsonPath = path.join(fixtureDir, 'fixture.json');
  let mode: string | undefined;
  let baseTemplate: string | undefined;
  try {
    const content = await fs.readFile(fixtureJsonPath, 'utf-8');
    const json = JSON.parse(content);
    if (!json.evalId) errors.push('fixture.json missing evalId');
    if (!json.name) errors.push('fixture.json missing name');
    if (!json.mode) errors.push('fixture.json missing mode');
    if (!json.task) errors.push('fixture.json missing task');
    mode = json.mode;
    baseTemplate = json.baseTemplate;
  } catch (e) {
    errors.push(`fixture.json error: ${e}`);
  }

  const projectDir = path.join(fixtureDir, 'project');
  try {
    await fs.access(projectDir);
  } catch {
    errors.push('project/ directory does not exist');
  }

  const stubTemplates = new Set([
    'maestro-ios-blank',
    'maestro-ios-wdio-stub',
    'wdio-log-interpret-stub',
    'android-ios-port-stub',
    'wdio-run-scope-stub',
    'mobile-root-cause-stub',
    'mobile-efficient-debug-stub',
    'mobile-nondestructive-fix-stub',
  ]);
  const requiresPackageJson = !stubTemplates.has(baseTemplate ?? '');
  if (requiresPackageJson) {
    const packageJsonPath = path.join(projectDir, 'package.json');
    try {
      await fs.access(packageJsonPath);
    } catch {
      errors.push('project/package.json does not exist');
    }
  }

  if (mode === 'fix') {
    const logPath = path.join(fixtureDir, 'failure.log');
    try {
      const stat = await fs.stat(logPath);
      if (stat.size < 100) {
        errors.push('failure.log exists but seems too small');
      }
    } catch {
      errors.push('failure.log does not exist (required for fix-mode)');
    }
  }

  return { evalId, valid: errors.length === 0, errors };
}

async function main() {
  const baseDir = path.join(__dirname, '..');
  const targetIds = process.argv.slice(2).filter((arg) => /^E\d+$/.test(arg));
  const evalIds =
    targetIds.length > 0
      ? targetIds
      : (await fs.readdir(path.join(baseDir, 'fixtures')))
          .filter((entry) => /^E\d+$/.test(entry))
          .sort((a, b) => Number(a.slice(1)) - Number(b.slice(1)));

  console.log(`Validating ${evalIds.length} eval fixtures...\n`);

  let passed = 0;
  let failed = 0;

  for (const evalId of evalIds) {
    const result = await validateFixture(evalId, baseDir);
    if (result.valid) {
      console.log(`✓ ${evalId}`);
      passed++;
    } else {
      console.log(`✗ ${evalId}`);
      result.errors.forEach((e) => console.log(`    - ${e}`));
      failed++;
    }
  }

  console.log(`\n${passed} passed, ${failed} failed out of ${evalIds.length} fixtures`);

  if (failed > 0) {
    process.exit(1);
  }
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
