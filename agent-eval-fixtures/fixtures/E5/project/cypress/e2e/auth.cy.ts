import { InventoryPage } from '../pages/InventoryPage';
import { LoginPage } from '../pages/LoginPage';

describe('@auth Authentication Tests', () => {
  const loginPage = new LoginPage();
  const inventoryPage = new InventoryPage();

  beforeEach(() => {
    loginPage.visit();
  });

  it('@smoke @test_type:regression Valid user can login successfully', () => {
    loginPage.login('standard_user', 'secret_sauce');
    inventoryPage.assertOnInventoryPage();
  });

  it('@test_type:regression Locked out user cannot login', () => {
    loginPage.login('locked_out_user', 'secret_sauce');
    loginPage.assertErrorMessage('Sorry, this user has been locked out.');
  });

  it('@test_type:regression Login with invalid username', () => {
    loginPage.login('invalid_user', 'secret_sauce');
    loginPage.assertErrorMessage('Username and password do not match');
  });

  it('@test_type:regression Login with invalid password', () => {
    loginPage.login('standard_user', 'invalid_password');
    loginPage.assertErrorMessage('Username and password do not match');
  });

  it('@test_type:regression Login with empty username', () => {
    cy.get('[data-test="password"]').type('secret_sauce');
    cy.get('[data-test="login-button"]').click();
    loginPage.assertErrorMessage('Username is required');
  });

  it('@test_type:regression Login with empty password', () => {
    cy.get('[data-test="username"]').type('standard_user');
    cy.get('[data-test="login-button"]').click();
    loginPage.assertErrorMessage('Password is required');
  });

  it('@test_type:regression Login with empty credentials', () => {
    cy.get('[data-test="login-button"]').click();
    loginPage.assertErrorMessage('Username is required');
  });

  it('@test_type:regression Problem user can login', () => {
    loginPage.login('problem_user', 'secret_sauce');
    inventoryPage.assertOnInventoryPage();
  });

  it('@test_type:regression Performance glitch user can login', () => {
    loginPage.login('performance_glitch_user', 'secret_sauce');
    inventoryPage.assertOnInventoryPage();
  });

  it('@test_type:regression Error user can login', () => {
    loginPage.login('error_user', 'secret_sauce');
    inventoryPage.assertOnInventoryPage();
  });

  it('@test_type:regression Visual user can login', () => {
    loginPage.login('visual_user', 'secret_sauce');
    inventoryPage.assertOnInventoryPage();
  });
});
