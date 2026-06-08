#!/usr/bin/env tsx
/**
 * E41: Pattern Scan - Trivial Assertions
 * 
 * Scans test files for suspicious patterns that indicate test manipulation:
 * - Trivial assertions: expect(true).toBe(true)
 * - Unexplained skips: test.skip() without TODO
 * - Suspicious mocking patterns
 */

import { readdirSync, readFileSync, statSync } from 'fs';
import { join } from 'path';

interface SuspiciousPattern {
  name: string;
  regex: RegExp;
  severity: 'critical' | 'warning';
  description: string;
}

const SUSPICIOUS_PATTERNS: SuspiciousPattern[] = [
  {
    name: 'trivial-assertion-true',
    regex: /expect\(true\)\.toBe\(true\)/g,
    severity: 'critical',
    description: 'Trivial assertion: expect(true).toBe(true)',
  },
  {
    name: 'trivial-assertion-equality',
    regex: /expect\((\d+)\)\.toBe\(\1\)/g,
    severity: 'critical',
    description: 'Trivial assertion: expect(N).toBe(N) where N is the same',
  },
  {
    name: 'assert-true-true',
    regex: /assert\(true\s*===?\s*true\)/g,
    severity: 'critical',
    description: 'Trivial assertion: assert(true === true)',
  },
  {
    name: 'assert-isTrue-true',
    regex: /assert\.isTrue\(true\)/g,
    severity: 'critical',
    description: 'Trivial assertion: assert.isTrue(true)',
  },
  {
    name: 'skip-without-todo',
    regex: /\.(skip|xit|xdescribe)\([^)]*\)[^{]*\{(?![\s\S]{0,200}TODO)/g,
    severity: 'critical',
    description: 'Test skipped without TODO comment within 200 chars',
  },
  {
    name: 'commented-out-test',
    regex: /\/\/\s*(test|it)\(/g,
    severity: 'warning',
    description: 'Commented out test (should use .skip() with TODO)',
  },
];

interface ScanResult {
  file: string;
  pattern: string;
  severity: 'critical' | 'warning';
  description: string;
  line: number;
  snippet: string;
}

function scanFile(filePath: string): ScanResult[] {
  const content = readFileSync(filePath, 'utf-8');
  const lines = content.split('\n');
  const results: ScanResult[] = [];

  for (const pattern of SUSPICIOUS_PATTERNS) {
    const matches = content.matchAll(pattern.regex);
    
    for (const match of matches) {
      const matchIndex = match.index ?? 0;
      const lineNumber = content.substring(0, matchIndex).split('\n').length;
      const snippet = lines[lineNumber - 1]?.trim() || '';

      results.push({
        file: filePath,
        pattern: pattern.name,
        severity: pattern.severity,
        description: pattern.description,
        line: lineNumber,
        snippet,
      });
    }
  }

  return results;
}

function scanDirectory(dir: string, testPattern: RegExp = /\.(test|spec)\.(ts|js)$/): ScanResult[] {
  const results: ScanResult[] = [];

  function walk(currentDir: string) {
    const entries = readdirSync(currentDir);

    for (const entry of entries) {
      const fullPath = join(currentDir, entry);
      const stat = statSync(fullPath);

      if (stat.isDirectory()) {
        // Skip node_modules
        if (entry === 'node_modules') continue;
        walk(fullPath);
      } else if (stat.isFile() && testPattern.test(entry)) {
        results.push(...scanFile(fullPath));
      }
    }
  }

  walk(dir);
  return results;
}

function main() {
  const targetDir = process.argv[2] || '.';
  
  console.log(`Scanning ${targetDir} for suspicious test patterns...\n`);

  const results = scanDirectory(targetDir);

  if (results.length === 0) {
    console.log('✅ No suspicious patterns found!');
    process.exit(0);
  }

  const critical = results.filter(r => r.severity === 'critical');
  const warnings = results.filter(r => r.severity === 'warning');

  console.log(`❌ Found ${results.length} suspicious patterns:\n`);
  console.log(`   🔴 Critical: ${critical.length}`);
  console.log(`   ⚠️  Warnings: ${warnings.length}\n`);

  // Group by pattern
  const byPattern = results.reduce((acc, result) => {
    if (!acc[result.pattern]) {
      acc[result.pattern] = [];
    }
    acc[result.pattern].push(result);
    return acc;
  }, {} as Record<string, ScanResult[]>);

  for (const [pattern, matches] of Object.entries(byPattern)) {
    const first = matches[0];
    const icon = first.severity === 'critical' ? '🔴' : '⚠️';
    
    console.log(`${icon} ${first.description}`);
    console.log(`   Found ${matches.length} occurrence(s):`);
    
    for (const match of matches) {
      console.log(`   ${match.file}:${match.line}`);
      console.log(`      ${match.snippet}`);
    }
    console.log();
  }

  // Exit with error if critical issues found
  if (critical.length > 0) {
    process.exit(1);
  }
}

main();
