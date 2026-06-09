export class AndroidLoginScreen {
  /** Android: uses UiSelector resource-id pattern. The iOS equivalent should use ~accessibilityId with the matching iOS label. */
  async tapLogin(): Promise<void> {
    const login = await $(
      'android=new UiSelector().resourceId("com.fundsindia.b2c:id/btn_login")',
    );
    await login.waitForDisplayed({ timeout: 10_000 });
    await login.click();
  }

  /** Android-only helper — do not port to iOS. */
  async tapForgotPassword(): Promise<void> {
    const forgot = await $(
      'android=new UiSelector().resourceId("com.fundsindia.b2c:id/btn_forgot_password")',
    );
    await forgot.waitForDisplayed({ timeout: 10_000 });
    await forgot.click();
  }
}
