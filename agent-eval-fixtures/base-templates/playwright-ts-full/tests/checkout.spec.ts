import { expect, test } from '@playwright/test';
import { CheckoutCompletePage, CheckoutOverviewPage, CheckoutPage } from '../pages/CheckoutPage';
import { InventoryPage } from '../pages/InventoryPage';
import { LoginPage } from '../pages/LoginPage';

test.describe('Checkout Flow Tests', () => {
  let loginPage: LoginPage;
  let inventoryPage: InventoryPage;
  let checkoutPage: CheckoutPage;
  let overviewPage: CheckoutOverviewPage;
  let completePage: CheckoutCompletePage;

  test.beforeEach(async ({ page }) => {
    loginPage = new LoginPage(page);
    inventoryPage = new InventoryPage(page);
    checkoutPage = new CheckoutPage(page);
    overviewPage = new CheckoutOverviewPage(page);
    completePage = new CheckoutCompletePage(page);

    await loginPage.goto();
    await loginPage.login('standard_user', 'secret_sauce');
    await inventoryPage.addProductToCart('sauce-labs-backpack');
    await inventoryPage.goToCart();
  });

  test.describe('Checkout Information Step', () => {
    test('@checkout @test_type:regression Checkout requires first name', async ({ page }) => {
      await page.click('[data-test="checkout"]');
      await checkoutPage.fillCheckoutForm('', 'Doe', '12345');
      await checkoutPage.continueCheckout();
      await checkoutPage.assertErrorMessage('First Name is required');
    });

    test('@checkout @test_type:regression Checkout requires last name', async ({ page }) => {
      await page.click('[data-test="checkout"]');
      await checkoutPage.fillCheckoutForm('John', '', '12345');
      await checkoutPage.continueCheckout();
      await checkoutPage.assertErrorMessage('Last Name is required');
    });

    test('@checkout @test_type:regression Checkout requires postal code', async ({ page }) => {
      await page.click('[data-test="checkout"]');
      await checkoutPage.fillCheckoutForm('John', 'Doe', '');
      await checkoutPage.continueCheckout();
      await checkoutPage.assertErrorMessage('Postal Code is required');
    });

    test('@checkout @smoke @test_type:regression Valid form proceeds to overview', async ({ page }) => {
      await page.click('[data-test="checkout"]');
      await checkoutPage.fillCheckoutForm('John', 'Doe', '12345');
      await checkoutPage.continueCheckout();
      await overviewPage.assertOnOverviewPage();
    });

    test('@checkout @test_type:regression Cancel returns to cart', async ({ page }) => {
      await page.click('[data-test="checkout"]');
      await checkoutPage.cancelCheckout();
      await expect(page).toHaveURL(/cart.html/);
    });
  });

  test.describe('Checkout Overview Step', () => {
    test.beforeEach(async ({ page }) => {
      await page.click('[data-test="checkout"]');
      await checkoutPage.fillCheckoutForm('John', 'Doe', '12345');
      await checkoutPage.continueCheckout();
    });

    test('@checkout @test_type:regression Overview displays correct item', async ({ page }) => {
      const itemName = page.locator('.inventory_item_name');
      await expect(itemName).toContainText('Sauce Labs Backpack');
    });

    test('@checkout @test_type:regression Overview displays payment information', async ({ page }) => {
      const paymentInfo = page.locator('[data-test="payment-info-value"]');
      await expect(paymentInfo).toContainText('SauceCard');
    });

    test('@checkout @test_type:regression Overview displays shipping information', async ({ page }) => {
      const shippingInfo = page.locator('[data-test="shipping-info-value"]');
      await expect(shippingInfo).toContainText('Free Pony Express Delivery');
    });

    test('@checkout @test_type:regression Overview calculates correct subtotal', async ({ page }) => {
      const subtotal = await overviewPage.asyncGetSubtotal();
      expect(subtotal).toBe(29.99);
    });

    test('@checkout @test_type:regression Overview calculates tax', async ({ page }) => {
      const tax = await overviewPage.asyncGetTax();
      expect(tax).toBeGreaterThan(0);
    });

    test('@checkout @test_type:regression Overview calculates total correctly', async ({ page }) => {
      const subtotal = await overviewPage.asyncGetSubtotal();
      const tax = await overviewPage.asyncGetTax();
      const total = await overviewPage.asyncGetTotal();

      expect(total).toBeCloseTo(subtotal + tax, 2);
    });

    test('@checkout @smoke @test_type:regression Finish completes the order', async ({ page }) => {
      await overviewPage.finishOrder();
      await completePage.assertOnCompletePage();
    });

    test('@checkout @test_type:regression Cancel returns to inventory', async ({ page }) => {
      await overviewPage.cancelOrder();
      await inventoryPage.assertOnInventoryPage();
    });
  });

  test.describe('Checkout Complete Step', () => {
    test.beforeEach(async ({ page }) => {
      await page.click('[data-test="checkout"]');
      await checkoutPage.fillCheckoutForm('John', 'Doe', '12345');
      await checkoutPage.continueCheckout();
      await overviewPage.finishOrder();
    });

    test('@checkout @smoke @test_type:regression Complete page shows success message', async ({ page }) => {
      await completePage.assertOrderComplete();
    });

    test('@checkout @test_type:regression Complete page shows dispatch message', async ({ page }) => {
      const dispatchText = page.locator('[data-test="complete-text"]');
      await expect(dispatchText).toContainText('dispatched');
    });

    test('@checkout @test_type:regression Back to products returns to inventory', async ({ page }) => {
      await completePage.backToProducts();
      await inventoryPage.assertOnInventoryPage();
    });

    test('@checkout @test_type:regression Cart is empty after order completion', async ({ page }) => {
      await completePage.backToProducts();
      const cartBadge = await inventoryPage.getCartItemCount();
      expect(cartBadge).toBe(0);
    });
  });

  test.describe('Full Checkout Flow', () => {
    test('@checkout @e2e @smoke @test_type:regression Complete purchase flow', async ({ page }) => {
      // We're on cart page from beforeEach, need to go back to inventory first
      await page.click('[data-test="continue-shopping"]');
      await inventoryPage.assertOnInventoryPage();

      // The backpack is already in cart from beforeEach, add bike light
      await inventoryPage.addProductToCart('sauce-labs-bike-light');

      // Go to checkout
      await inventoryPage.goToCart();
      await page.click('[data-test="checkout"]');

      // Fill form
      await checkoutPage.fillCheckoutForm('Jane', 'Smith', '54321');
      await checkoutPage.continueCheckout();

      // Verify overview
      await overviewPage.assertOnOverviewPage();
      const total = await overviewPage.asyncGetTotal();
      expect(total).toBeGreaterThan(0);

      // Complete order
      await overviewPage.finishOrder();
      await completePage.assertOrderComplete();

      // Return to products
      await completePage.backToProducts();
      await inventoryPage.assertOnInventoryPage();
    });

    test('@checkout @e2e @test_type:regression Order with all 6 products', async ({ page }) => {
      // We're on cart page from beforeEach, need to go back to inventory first
      await page.click('[data-test="continue-shopping"]');
      await inventoryPage.assertOnInventoryPage();

      // Backpack is already in cart from beforeEach, add the other 5
      const products = [
        'sauce-labs-bike-light',
        'sauce-labs-bolt-t-shirt',
        'sauce-labs-fleece-jacket',
        'sauce-labs-onesie',
        'test.allthethings()-t-shirt-(red)'
      ];

      for (const product of products) {
        await inventoryPage.addProductToCart(product);
      }

      await inventoryPage.assertCartItemCount(6);

      // Complete checkout
      await inventoryPage.goToCart();
      await page.click('[data-test="checkout"]');
      await checkoutPage.fillCheckoutForm('Test', 'User', '99999');
      await checkoutPage.continueCheckout();
      await overviewPage.finishOrder();
      await completePage.assertOrderComplete();
    });

    test('@checkout @e2e @test_type:regression Verify cart cleared after purchase', async ({ page }) => {
      // We're on cart page from beforeEach, need to go back to inventory first
      await page.click('[data-test="continue-shopping"]');
      await inventoryPage.assertOnInventoryPage();

      // Backpack is already in cart from beforeEach
      await inventoryPage.goToCart();
      await page.click('[data-test="checkout"]');
      await checkoutPage.fillCheckoutForm('User', 'Test', '11111');
      await checkoutPage.continueCheckout();
      await overviewPage.finishOrder();
      await completePage.backToProducts();

      await inventoryPage.assertCartItemCount(0);
    });
  });
});
