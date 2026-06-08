export class LoginPage {
  // Selectors
  readonly usernameInput = '[data-test="username"]';
  readonly passwordInput = '[data-test="password"]';
  readonly loginButton = '[data-test="login-button"]';
  readonly errorMessage = '[data-test="error"]';

  visit() {
    cy.visit('/');
  }

  login(username: string, password: string) {
    cy.get(this.usernameInput).type(username);
    cy.get(this.passwordInput).type(password);
    cy.get(this.loginButton).click();
  }

  assertErrorMessage(message: string) {
    cy.get(this.errorMessage).should('contain.text', message);
  }

  assertOnLoginPage() {
    cy.get(this.loginButton).should('be.visible');
  }
}
