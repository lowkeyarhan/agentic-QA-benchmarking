import { expect, test } from '@playwright/test';
import { CartPage } from '../pages/CartPage';
import { InventoryPage } from '../pages/InventoryPage';
import { LoginPage } from '../pages/LoginPage';

test.describe('Problem User Cart Tests', () => {
  let loginPage: LoginPage;
  let inventoryPage: InventoryPage;
  let cartPage: CartPage;

  test.beforeEach(async ({ page }) => {
    loginPage = new LoginPage(page);
    inventoryPage = new InventoryPage(page);
    cartPage = new CartPage(page);
    await loginPage.goto();
  });

  test('Problem user can add product to cart', { tag: ['@feature:cart', '@priority:high', '@test_type:e2e', '@user:problem_user'] }, async ({ page }) => {
    // Login as problem_user
    await loginPage.login('problem_user', 'secret_sauce');
    await inventoryPage.assertOnInventoryPage();

    // Add a product to the cart
    await inventoryPage.addProductToCart('sauce-labs-backpack');

    // Verify cart badge shows 1 item
    await inventoryPage.assertCartItemCount(1);

    // Navigate to cart and verify item is present
    await inventoryPage.goToCart();
    await cartPage.assertOnCartPage();
    await cartPage.assertCartItemCount(1);

    // Verify the correct product was added
    const itemNames = await cartPage.getCartItemNames();
    expect(itemNames).toContain('Sauce Labs Backpack');
  });

  test('Problem user can add multiple products to cart', { tag: ['@feature:cart', '@priority:medium', '@test_type:e2e', '@user:problem_user'] }, async ({ page }) => {
    // Login as problem_user
    await loginPage.login('problem_user', 'secret_sauce');
    await inventoryPage.assertOnInventoryPage();

    // Add multiple products to the cart
    await inventoryPage.addProductToCart('sauce-labs-backpack');
    await inventoryPage.addProductToCart('sauce-labs-bike-light');
    await inventoryPage.addProductToCart('sauce-labs-bolt-t-shirt');

    // Verify cart badge shows 3 items
    await inventoryPage.assertCartItemCount(3);

    // Navigate to cart and verify all items are present
    await inventoryPage.goToCart();
    await cartPage.assertOnCartPage();
    await cartPage.assertCartItemCount(3);

    // Verify all products were added
    const itemNames = await cartPage.getCartItemNames();
    expect(itemNames).toContain('Sauce Labs Backpack');
    expect(itemNames).toContain('Sauce Labs Bike Light');
    expect(itemNames).toContain('Sauce Labs Bolt T-Shirt');
  });
});
