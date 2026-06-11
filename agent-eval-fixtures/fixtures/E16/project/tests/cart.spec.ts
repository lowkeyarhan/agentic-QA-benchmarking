import { expect, test } from '@playwright/test';
import { CartPage } from '../pages/CartPage';
import { InventoryPage } from '../pages/InventoryPage';
import { LoginPage } from '../pages/LoginPage';

test.describe('Shopping Cart Tests', () => {
  let loginPage: LoginPage;
  let inventoryPage: InventoryPage;
  let cartPage: CartPage;

  test.beforeEach(async ({ page }) => {
    loginPage = new LoginPage(page);
    inventoryPage = new InventoryPage(page);
    cartPage = new CartPage(page);
    await loginPage.goto();
    await loginPage.login('standard_user', 'secret_sauce');
  });

  test('@cart @smoke @test_type:regression Cart is empty initially', async ({ page }) => {
    await inventoryPage.goToCart();
    await cartPage.assertOnCartPage();
    await cartPage.assertCartItemCount(0);
  });

  test('@cart @test_type:regression Added items appear in cart', async ({ page }) => {
    await inventoryPage.addProductToCart('sauce-labs-backpack');
    await inventoryPage.goToCart();

    await cartPage.assertCartItemCount(1);

    const itemNames = await cartPage.getCartItemNames();
    expect(itemNames).toContain('Sauce Labs Backpack');
  });

  test('@cart @test_type:regression Multiple items can be added to cart', async ({ page }) => {
    await inventoryPage.addProductToCart('sauce-labs-backpack');
    await inventoryPage.addProductToCart('sauce-labs-bike-light');
    await inventoryPage.addProductToCart('sauce-labs-bolt-t-shirt');

    await inventoryPage.goToCart();
    await cartPage.assertCartItemCount(3);
  });

  test('@cart @test_type:regression Items can be removed from cart', async ({ page }) => {
    await inventoryPage.addProductToCart('sauce-labs-backpack');
    await inventoryPage.goToCart();

    await cartPage.assertCartItemCount(1);
    await cartPage.removeCartItem(0);
    await cartPage.assertCartItemCount(0);
  });

  test('@cart @test_type:regression Cart shows correct item details', async ({ page }) => {
    await inventoryPage.addProductToCart('sauce-labs-backpack');
    await inventoryPage.goToCart();

    const cartItem = page.locator('.cart_item').first();

    await expect(cartItem.locator('.inventory_item_name')).toContainText('Sauce Labs Backpack');
    await expect(cartItem.locator('.inventory_item_desc')).toBeVisible();
    await expect(cartItem.locator('.inventory_item_price')).toContainText('$29.99');
  });

  test('@cart @test_type:regression Cart badge updates when items removed', async ({ page }) => {
    await inventoryPage.addProductToCart('sauce-labs-backpack');
    await inventoryPage.addProductToCart('sauce-labs-bike-light');
    await inventoryPage.assertCartItemCount(2);

    await inventoryPage.goToCart();
    await cartPage.removeCartItem(0);
    // Wait for cart to update
    await cartPage.assertCartItemCount(1);

    // Go back to inventory to check badge
    await cartPage.continueShopping();
    await inventoryPage.assertCartItemCount(1);
  });

  test('@cart @smoke @test_type:regression Continue shopping returns to inventory', async ({ page }) => {
    await inventoryPage.addProductToCart('sauce-labs-backpack');
    await inventoryPage.goToCart();
    await cartPage.continueShopping();

    await inventoryPage.assertOnInventoryPage();
  });

  test('@cart @test_type:regression Checkout button is visible in cart', async ({ page }) => {
    await inventoryPage.addProductToCart('sauce-labs-backpack');
    await inventoryPage.goToCart();

    await expect(cartPage.checkoutButton).toBeVisible();
  });

  test('@cart @smoke @test_type:regression Can navigate to checkout from cart', async ({ page }) => {
    await inventoryPage.addProductToCart('sauce-labs-backpack');
    await inventoryPage.goToCart();
    await cartPage.goToCheckout();

    await expect(page).toHaveURL(/checkout-step-one.html/);
  });

  test('@cart @test_type:regression Cart displays quantity of 1 for each item', async ({ page }) => {
    await inventoryPage.addProductToCart('sauce-labs-backpack');
    await inventoryPage.goToCart();

    const quantity = page.locator('.cart_quantity').first();
    await expect(quantity).toContainText('1');
  });

  test('@cart @test_type:regression Empty cart displays continue shopping button', async ({ page }) => {
    await inventoryPage.goToCart();
    await expect(cartPage.continueShoppingButton).toBeVisible();
  });

  test('@cart @test_type:regression Cart link navigates to cart page', async ({ page }) => {
    await inventoryPage.goToCart();
    await expect(page).toHaveURL(/cart.html/);
  });

  test('@cart @test_type:regression Cart preserves items when navigating away and back', async ({ page }) => {
    await inventoryPage.addProductToCart('sauce-labs-backpack');
    await inventoryPage.addProductToCart('sauce-labs-bike-light');

    await inventoryPage.goToCart();
    await cartPage.assertCartItemCount(2);

    await cartPage.continueShopping();
    await inventoryPage.goToCart();

    await cartPage.assertCartItemCount(2);
  });

  test('@cart @test_type:regression Cart badge shows correct number of unique items', async ({ page }) => {
    // Add same item multiple times - should still be 1 (quantity-based)
    await inventoryPage.addProductToCart('sauce-labs-backpack');
    // The button has changed to "Remove", so we can't click it again
    // The badge should still show 1
    await inventoryPage.assertCartItemCount(1);

    // Add a different item
    await inventoryPage.addProductToCart('sauce-labs-bike-light');
    await inventoryPage.assertCartItemCount(2);
  });
});
