export class AndroidLoginScreen {
  async tapLogin(): Promise<void> {
    const login = await $('android=new UiSelector().resourceId("com.fundsindia.b2c:id/btn_login")');
    await login.waitForDisplayed({ timeout: 10_000 });
    await login.click();
  }
}
