export class LumpsumScreen {
  async assertLumpsumTitleVisible(): Promise<void> {
    const title = await $('~Lumpsum');
    await title.waitForDisplayed({ timeout: 10_000 });
  }

  async tapFirstSchemeAddIcon(): Promise<void> {
    throw new Error('Not implemented — implement using references/lumpsum-inspect-snippet.json');
  }
}
