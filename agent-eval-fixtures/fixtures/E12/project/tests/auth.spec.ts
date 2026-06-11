import { expect, test } from '@playwright/test';
import { InventoryPage } from '../pages/InventoryPage';
import { LoginPage } from '../pages/LoginPage';

test.describe('Authentication Tests', () => {
  let loginPage: LoginPage;
  let inventoryPage: InventoryPage;

  test.beforeEach(async ({ page }) => {
    loginPage = new LoginPage(page);
    inventoryPage = new InventoryPage(page);
    await loginPage.goto();
  });

  test('@auth @smoke @test_type:regression Valid user can login successfully', async ({ page }) => {
    await loginPage.login('standard_user', 'secret_sauce');
    await inventoryPage.assertOnInventoryPage();
  });

  test('@auth @test_type:regression Locked out user cannot login', async ({ page }) => {
    await loginPage.login('locked_out_user', 'secret_sauce');
    await loginPage.assertErrorMessage('Sorry, this user has been locked out.');
  });

  test('@auth @test_type:regression Login with invalid username', async ({ page }) => {
    await loginPage.login('invalid_user', 'secret_sauce');
    await loginPage.assertErrorMessage('Username and password do not match');
  });

  test('@auth @test_type:regression Login with invalid password', async ({ page }) => {
    await loginPage.login('standard_user', 'invalid_password');
    await loginPage.assertErrorMessage('Username and password do not match');
  });

  test('@auth @test_type:regression Login with empty username', async ({ page }) => {
    await loginPage.login('', 'secret_sauce');
    await loginPage.assertErrorMessage('Username is required');
  });

  test('@auth @test_type:regression Login with empty password', async ({ page }) => {
    await loginPage.login('standard_user', '');
    await loginPage.assertErrorMessage('Password is required');
  });

  test('@auth @test_type:regression Login with empty credentials', async ({ page }) => {
    await loginPage.login('', '');
    await loginPage.assertErrorMessage('Username is required');
  });

  test.skip('@auth @smoke @test_type:regression User can logout', async ({ page }) => {
    // TODO: Menu button tests are flaky - needs investigation
    await loginPage.login('standard_user', 'secret_sauce');
    await inventoryPage.assertOnInventoryPage();
    await inventoryPage.logout();
    await loginPage.assertOnLoginPage();
  });

  test('@auth @test_type:regression Problem user can login', async ({ page }) => {
    await loginPage.login('problem_user', 'secret_sauce');
    await inventoryPage.assertOnInventoryPage();
  });

  test('@auth @test_type:regression Performance glitch user can login', async ({ page }) => {
    await loginPage.login('performance_glitch_user', 'secret_sauce');
    await inventoryPage.assertOnInventoryPage();
  });

  test('@auth @test_type:regression Error user can login', async ({ page }) => {
    await loginPage.login('error_user', 'secret_sauce');
    await inventoryPage.assertOnInventoryPage();
  });

  test('@auth @test_type:regression Visual user can login', async ({ page }) => {
    await loginPage.login('visual_user', 'secret_sauce');
    await inventoryPage.assertOnInventoryPage();
  });
});
