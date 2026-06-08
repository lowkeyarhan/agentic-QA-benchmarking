#!/usr/bin/env tsx

import * as fs from "fs";
import * as path from "path";
import { gradeMaestroWdioTranslation } from "../../cli/src/utils/maestroWdioGrade.ts";

const DEFAULT_EVAL_ID = "E101";

function main(): void {
  const evalId = process.argv[2] || DEFAULT_EVAL_ID;
  const filePath =
    process.argv[3] ||
    path.join(
      process.cwd(),
      "agent-eval-fixtures",
      "fixtures",
      evalId,
      "project",
      "pages",
      "lumpsum.screen.ts"
    );

  if (!fs.existsSync(filePath)) {
    console.error(`File not found: ${filePath}`);
    process.exit(1);
  }

  const source = fs.readFileSync(filePath, "utf-8");
  const result = gradeMaestroWdioTranslation(source);

  console.log(`Grading ${evalId}: ${path.basename(filePath)}`);
  for (const w of result.warnings) {
    console.log(`  ⚠️  ${w}`);
  }

  if (result.pass) {
    console.log("  ✅ PASS — Maestro→WDIO translation criteria met");
    process.exit(0);
  }

  for (const e of result.errors) {
    console.log(`  ❌ ${e}`);
  }
  process.exit(1);
}

main();
