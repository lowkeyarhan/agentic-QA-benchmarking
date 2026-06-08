#!/usr/bin/env tsx

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
} from "../../cli/src/utils/prodRegressionGrades.ts";
import { gradeMaestroWdioTranslation } from "../../cli/src/utils/maestroWdioGrade.ts";

function assert(label: string, pass: boolean): void {
  if (!pass) {
    console.error(`FAIL: ${label}`);
    process.exit(1);
  }
  console.log(`✅ ${label}`);
}

const goodE101 = `async tapFirstSchemeAddIcon() {
  const icons = await $$('~mfAddStock');
  await icons[0].click();
}`;

const badE101 = `await $('-ios predicate string:label == "mfAddStock" AND type == "XCUIElementTypeButton"');`;

const goodE102 = `didRun: yes\npassed: 1\nfailed: 0\nTest ran — Spec Files shows 1 passed.`;

const badE102 = "The test hasn't actually started.";

const goodE103 = `async tapLogin() { await $('~SignInButton').click(); }`;

const badE103 = `$('android=new UiSelector().resourceId("com.fundsindia.b2c:id/btn_login")')`;

const goodE104 = "npx wdio run wdio.conf.ts --spec test/specs/cart.spec.ts --workers=1";

const badE104 = "npx wdio run wdio.conf.ts --spec test/specs/**/*.spec.ts";

const goodE105 = `failingMethod: completeDocumentUpload
wrongSelector: ~UploadButton
correctSelectorFromHierarchy: ~SubmitUpload
rootCause: Test used UploadButton but hierarchy shows SubmitUpload
proposedFix: Change to $('~SubmitUpload')`;

const badE105 = "grep the log and rerun wdio 5 times until it works";

const goodE106 = `1. mcp__maestro__inspect_screen on the cart screen
2. Update selector in products.page.ts from inspect evidence
3. Rerun the single failing spec once with --workers=1`;

const badE106 = `1. grep -E Error /tmp/wdio.log
2. tail -100 /tmp/wdio.log
3. rerun test
4. grep again
5. edit spec`;

const goodE107 = `export class DocumentUploadScreen {
  async fillShipping(address: string): Promise<void> {
    await $('~ShippingAddress').setValue(address);
  }
  async submitOrder(): Promise<void> {
    await $('~PlaceOrder').click();
  }
  async verifyConfirmation(): Promise<void> {
    await $('~OrderConfirmed').waitForDisplayed({ timeout: 10_000 });
  }
  async completeDocumentUpload(): Promise<void> {
    await $('~SubmitUpload').click();
  }
}`;

const badE107 = `export class DocumentUploadScreen {
  async completeDocumentUpload() {
    await $('~UploadButton').click();
  }
}`;

assert("E101 good pattern passes", gradeMaestroWdioTranslation(goodE101).pass);
assert("E101 bad pattern fails", !gradeMaestroWdioTranslation(badE101).pass);
assert("E102 good analysis passes", gradeWdioLogInterpretation(goodE102).pass);
assert("E102 denial fails", !gradeWdioLogInterpretation(badE102).pass);
assert("E103 good port passes", gradeIosPortFromAndroid(goodE103).pass);
assert("E103 android copy fails", !gradeIosPortFromAndroid(badE103).pass);
assert("E104 scoped command passes", gradeWdioRunScope(goodE104).pass);
assert("E104 full suite fails", !gradeWdioRunScope(badE104).pass);
assert("E105 root cause passes", gradeRootCauseAnalysis(goodE105).pass);
assert("E105 grep loop fails", !gradeRootCauseAnalysis(badE105).pass);
assert("E106 efficient plan passes", gradeEfficientDebugPlan(goodE106).pass);
assert("E106 slow plan fails", !gradeEfficientDebugPlan(badE106).pass);
assert("E107 non-destructive passes", gradeNonDestructiveFix(goodE107).pass);
assert("E107 gutted file fails", !gradeNonDestructiveFix(badE107).pass);

const goodE108 = `1. npx wdio run wdio.conf.ts --spec mobile/tests/android/b2c-onboarding-android.spec.ts --workers=1
2. Read Spec Files summary line for pass/fail counts
3. Report passed and failed totals to the user`;

const badE108 = `1. grep -E Error /tmp/wdio.log
2. tail -200 /tmp/wdio.log
3. npx wdio run wdio.conf.ts --spec mobile/tests/android/**/*.spec.ts
4. grep again
5. rerun wdio full suite`;

const goodE109 = `1. mcp__maestro__list_devices
2. Select emulator-5554 (port 5554) — not emulator-5556
3. mcp__maestro__inspect_screen on emulator-5554
4. Report Analysis tab state`;

const badE109 = `1. adb devices
2. Use emulator-5556 for inspect and tap`;

const goodE113 = `1. mcp__maestro__inspect_screen on upload step
2. Fix selector in b2c-onboarding-android page object (~SubmitUpload)
3. Rerun once: npx wdio --spec mobile/tests/android/onboarding/b2c-onboarding-android.spec.ts --workers=1`;

const badE113 = `1. Rerun npx wdio --spec mobile/tests/android/onboarding/**/*.spec.ts
2. grep failures
3. Rerun full suite again`;

assert("E108 run strategy passes", gradeRunStrategy(goodE108).pass);
assert("E108 bash spiral fails", !gradeRunStrategy(badE108).pass);
assert("E109 device pin passes", gradeDevicePinPlan(goodE109).pass);
assert("E109 wrong emulator fails", !gradeDevicePinPlan(badE109).pass);
assert("E113 suite recovery passes", gradeSuiteNextSteps(goodE113).pass);
assert("E113 full suite first fails", !gradeSuiteNextSteps(badE113).pass);

console.log("\nProd regression grader smoke checks passed.");
