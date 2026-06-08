export class SettingsScreen {
  async tapBack(): Promise<void> {
    const back = await $('~Back');
    await back.waitForDisplayed({ timeout: 10_000 });
    await back.click();
  }

  async tapGeneralRow(): Promise<void> {
    const general = await $('~General');
    await general.waitForDisplayed({ timeout: 10_000 });
    await general.click();
  }
}
