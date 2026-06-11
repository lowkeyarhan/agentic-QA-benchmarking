import { expect, test } from '@playwright/test';
import { InventoryPage } from '../pages/InventoryPage';
import { LoginPage } from '../pages/LoginPage';

test.describe('Problem User - Add to Cart', () => {
  let loginPage: LoginPage;
  let inventoryPage: InventoryPage;

  test.beforeEach(async ({ page }) => {
    loginPage = new LoginPage(page);
    inventoryPage = new InventoryPage(page);

    await loginPage.goto();
    await loginPage.login('problem_user', 'secret_sauce');
    await inventoryPage.assertOnInventoryPage();
  });

  test('should add Sauce Labs Backpack to cart (@feature:cart @priority:high @test_type:e2e)', async ({ page }) => {
    const productId = 'sauce-labs-backpack';

    // Add product to cart
    await inventoryPage.addProductToCart(productId);

    // Verify cart badge shows 1 item
    await inventoryPage.assertCartItemCount(1);

    // Verify button changed to Remove
    await expect(inventoryPage.getRemoveButton(productId)).toBeVisible();
    await expect(inventoryPage.getAddToCartButton(productId)).not.toBeVisible();
  });
});
