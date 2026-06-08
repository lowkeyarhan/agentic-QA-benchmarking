#!/usr/bin/env tsx

import * as fs from "fs";
import * as path from "path";
import { gradeMaestroWdioTranslation } from "../../cli/src/utils/maestroWdioGrade.ts";
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
  type EvalGradeResult,
} from "../../cli/src/utils/prodRegressionGrades.ts";

const GRADE_PATHS: Record<string, string[]> = {
  E101: ["pages", "lumpsum.screen.ts"],
  E102: ["run-analysis.md"],
  E103: ["pages", "ios", "login.screen.ts"],
  E104: ["run-command.txt"],
  E105: ["root-cause.md"],
  E106: ["debug-plan.md"],
  E107: ["pages", "document-upload.screen.ts"],
  E108: ["run-strategy.md"],
  E109: ["device-plan.md"],
  E113: ["next-steps.md"],
};

function gradeFile(evalId: string, filePath: string): EvalGradeResult {
  const content = fs.readFileSync(filePath, "utf-8");
  switch (evalId) {
    case "E101":
      return gradeMaestroWdioTranslation(content);
    case "E102":
      return gradeWdioLogInterpretation(content);
    case "E103":
      return gradeIosPortFromAndroid(content);
    case "E104":
      return gradeWdioRunScope(content);
    case "E105":
      return gradeRootCauseAnalysis(content);
    case "E106":
      return gradeEfficientDebugPlan(content);
    case "E107":
      return gradeNonDestructiveFix(content);
    case "E108":
      return gradeRunStrategy(content);
    case "E109":
      return gradeDevicePinPlan(content);
    case "E113":
      return gradeSuiteNextSteps(content);
    default:
      return { pass: false, errors: [`No content grader for ${evalId}`], warnings: [] };
  }
}

function main(): void {
  const evalId = process.argv[2];
  if (!evalId || !GRADE_PATHS[evalId]) {
    console.error("Usage: grade-prod-regression.ts E101|E102|...|E113");
    process.exit(1);
  }

  const segments = GRADE_PATHS[evalId];
  const filePath =
    process.argv[3] ||
    path.join(process.cwd(), "agent-eval-fixtures", "fixtures", evalId, "project", ...segments);

  if (!fs.existsSync(filePath)) {
    console.error(`File not found: ${filePath}`);
    process.exit(1);
  }

  const result = gradeFile(evalId, filePath);
  console.log(`Grading ${evalId}: ${path.basename(filePath)}`);
  for (const w of result.warnings) {
    console.log(`  ⚠️  ${w}`);
  }
  if (result.pass) {
    console.log(`  ✅ PASS`);
    process.exit(0);
  }
  for (const e of result.errors) {
    console.log(`  ❌ ${e}`);
  }
  process.exit(1);
}

main();
