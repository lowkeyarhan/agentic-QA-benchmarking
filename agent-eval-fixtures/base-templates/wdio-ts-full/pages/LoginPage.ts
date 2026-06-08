import { $ } from '@wdio/globals';
import { expect } from 'expect-webdriverio';

export class LoginPage {
  get usernameInput() {
    return $('[data-test="username"]');
  }

  get passwordInput() {
    return $('[data-test="password"]');
  }

  get loginButton() {
    return $('[data-test="login-button"]');
  }

  get errorMessage() {
    return $('[data-test="error"]');
  }

  async open() {
    await browser.url('/');
  }

  async login(username: string, password: string) {
    await this.usernameInput.setValue(username);
    await this.passwordInput.setValue(password);
    await this.loginButton.click();
  }

  async assertErrorMessage(message: string) {
    await expect(this.errorMessage).toHaveText(message);
  }

  async assertOnLoginPage() {
    await expect(this.loginButton).toBeDisplayed();
  }
}
