#!/usr/bin/env tsx

import { gradeMaestroWdioTranslation } from "../../cli/src/utils/maestroWdioGrade.ts";

const badProdPattern = `
  async tapFirstSchemeAddIcon(): Promise<void> {
    const addIcon = await $(\`-ios predicate string:label == 'mfAddStock' AND type == 'XCUIElementTypeButton'\`);
    await addIcon.click();
  }
`;

const goodPattern = `
  async tapFirstSchemeAddIcon(): Promise<void> {
    const addIcon = await $$('~mfAddStock')[0];
    await addIcon.waitForDisplayed({ timeout: 10_000 });
    await addIcon.click();
  }
`;

function assert(condition: boolean, message: string): void {
  if (!condition) {
    console.error(`❌ ${message}`);
    process.exit(1);
  }
  console.log(`✅ ${message}`);
}

const bad = gradeMaestroWdioTranslation(badProdPattern);
assert(!bad.pass, "Prod-regression pattern is rejected by grader");
assert(
  bad.errors.some((e) => e.includes("XCUIElementType")),
  "Grader flags invented XCUIElementTypeButton"
);

const good = gradeMaestroWdioTranslation(goodPattern);
assert(good.pass, "Correct ~mfAddStock + index[0] pattern passes grader");

console.log("\nE101 smoke checks passed.");
