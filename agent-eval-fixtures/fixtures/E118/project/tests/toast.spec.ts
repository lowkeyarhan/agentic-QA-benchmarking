import { test, expect } from '@playwright/test';
import { LoginPage } from '../pages/LoginPage';
import { InventoryPage } from '../pages/InventoryPage';

let loginPage: LoginPage;
let inventoryPage: InventoryPage;

test.describe('Toast Notification Tests', () => {
  test.beforeEach(async ({ page }) => {
    loginPage = new LoginPage(page);
    inventoryPage = new InventoryPage(page);
    await loginPage.goto();
    await loginPage.login('standard_user', 'secret_sauce');
  });

  test('@toast @smoke @test_type:regression Add to cart shows toast notification', async ({ page }) => {
    await inventoryPage.addProductToCart('sauce-labs-backpack');

    // Toast notification that appears briefly
    const toast = page.locator('[data-test="toast-notification"]');
    await expect(toast).toBeVisible({ timeout: 5000 });
    await expect(toast).toHaveText('Item added to cart!');

    // Wait for toast to disappear
    await page.waitForTimeout(1000);
    await expect(toast).not.toBeVisible();
  });

  test('@toast @e2e @test_type:regression Toast appears for each add-to-cart', async ({ page }) => {
    await inventoryPage.addProductToCart('sauce-labs-backpack');
    const toast = page.locator('[data-test="toast-notification"]');
    await expect(toast).toBeVisible();

    // Wait for toast to disappear then add another
    await page.waitForTimeout(2500);

    await inventoryPage.addProductToCart('sauce-labs-bike-light');
    await expect(toast).toBeVisible();
    await expect(toast).toHaveText('Item added to cart!');
  });
});
