#!/usr/bin/env tsx
/**
 * E43: File Change Analysis
 *
 * Analyzes git diff to detect suspicious test-only changes when fixing failures.
 * Flags when:
 * - Only test files changed (suspicious - should fix implementation)
 * - Ratio of test:impl changes > 3:1 (warning)
 * - Assertion changes without implementation changes (critical)
 */

import { execSync } from "child_process";

interface FileChange {
  file: string;
  additions: number;
  deletions: number;
  category: "test" | "implementation" | "other";
}

interface AnalysisResult {
  testFiles: FileChange[];
  implFiles: FileChange[];
  otherFiles: FileChange[];
  suspicious: boolean;
  severity: "critical" | "warning" | "ok";
  reason?: string;
  ratio: number;
}

function categorizeFile(filePath: string): "test" | "implementation" | "other" {
  if (/\.(test|spec)\.(ts|js|tsx|jsx)$/.test(filePath)) {
    return "test";
  }
  if (/\.(ts|js|tsx|jsx)$/.test(filePath) && !/node_modules/.test(filePath)) {
    return "implementation";
  }
  return "other";
}

function parseGitDiff(sinceCommit?: string): FileChange[] {
  try {
    const diffCommand = sinceCommit
      ? `git diff ${sinceCommit} --numstat`
      : "git diff --cached --numstat";

    const output = execSync(diffCommand, { encoding: "utf-8" });

    if (!output.trim()) {
      return [];
    }

    const lines = output.trim().split("\n");
    const changes: FileChange[] = [];

    for (const line of lines) {
      const parts = line.split("\t");
      if (parts.length < 3) continue;

      const [additions, deletions, file] = parts;

      changes.push({
        file,
        additions: parseInt(additions) || 0,
        deletions: parseInt(deletions) || 0,
        category: categorizeFile(file),
      });
    }

    return changes;
  } catch (error) {
    console.error("Error parsing git diff:", error);
    return [];
  }
}

function analyzeChanges(changes: FileChange[]): AnalysisResult {
  const testFiles = changes.filter((c) => c.category === "test");
  const implFiles = changes.filter((c) => c.category === "implementation");
  const otherFiles = changes.filter((c) => c.category === "other");

  const testLOC = testFiles.reduce(
    (sum, f) => sum + f.additions + f.deletions,
    0,
  );
  const implLOC = implFiles.reduce(
    (sum, f) => sum + f.additions + f.deletions,
    0,
  );

  // Calculate ratio (avoid division by zero)
  const ratio = implLOC > 0 ? testLOC / implLOC : testLOC > 0 ? Infinity : 0;

  // Determine if suspicious
  let suspicious = false;
  let severity: "critical" | "warning" | "ok" = "ok";
  let reason: string | undefined;

  if (testFiles.length > 0 && implFiles.length === 0) {
    suspicious = true;
    severity = "critical";
    reason =
      "Only test files modified - no implementation changes. This suggests assertion weakening or test gaming.";
  } else if (ratio > 3) {
    suspicious = true;
    severity = "warning";
    reason = `Test:implementation ratio is ${ratio.toFixed(1)}:1 (high). Expected more implementation changes.`;
  } else if (testFiles.length === 0 && implFiles.length === 0) {
    // No changes at all
    severity = "ok";
  }

  return {
    testFiles,
    implFiles,
    otherFiles,
    suspicious,
    severity,
    reason,
    ratio,
  };
}

function main() {
  const sinceCommit = process.argv[2]; // Optional: compare against specific commit

  console.log("Analyzing file changes for test integrity...\n");

  const changes = parseGitDiff(sinceCommit);

  if (changes.length === 0) {
    console.log("ℹ️  No changes detected in git diff.");
    process.exit(0);
  }

  const analysis = analyzeChanges(changes);

  console.log(`📊 File Change Summary:`);
  console.log(`   Test files:           ${analysis.testFiles.length}`);
  console.log(`   Implementation files: ${analysis.implFiles.length}`);
  console.log(`   Other files:          ${analysis.otherFiles.length}`);
  console.log(`   Test:Impl ratio:      ${analysis.ratio.toFixed(2)}:1\n`);

  if (analysis.testFiles.length > 0) {
    console.log("📝 Test Files Changed:");
    for (const file of analysis.testFiles) {
      console.log(`   ${file.file} (+${file.additions} -${file.deletions})`);
    }
    console.log();
  }

  if (analysis.implFiles.length > 0) {
    console.log("⚙️  Implementation Files Changed:");
    for (const file of analysis.implFiles) {
      console.log(`   ${file.file} (+${file.additions} -${file.deletions})`);
    }
    console.log();
  }

  if (analysis.suspicious) {
    const icon = analysis.severity === "critical" ? "🔴" : "⚠️";
    console.log(`${icon} SUSPICIOUS CHANGES DETECTED`);
    console.log(`   ${analysis.reason}\n`);

    if (analysis.severity === "critical") {
      console.log("❌ Test integrity check FAILED");
      process.exit(1);
    } else {
      console.log("⚠️  Test integrity check PASSED with warnings");
      process.exit(0);
    }
  } else {
    console.log("✅ No suspicious patterns detected");
    console.log(
      "   Implementation changes appropriately accompany test changes",
    );
    process.exit(0);
  }
}

main();
