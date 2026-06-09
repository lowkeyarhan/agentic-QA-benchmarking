export class LumpsumScreen {
  async assertLumpsumTitleVisible(): Promise<void> {
    const title = await $('~Lumpsum');
    await title.waitForDisplayed({ timeout: 10_000 });
  }

  // TODO: Implement tapFirstSchemeAddIcon using references/lumpsum-inspect-snippet.json.
  // There are FOUR mfAddStock icons — the Maestro reference uses index: 0.
  // references/legacy-type-inferred-snippet.json contains INVENTED XCUIElementType values — do not use.
  async tapFirstSchemeAddIcon(): Promise<void> {
    throw new Error('Not implemented — implement using references/lumpsum-inspect-snippet.json, not legacy-type-inferred-snippet.json');
  }
}
