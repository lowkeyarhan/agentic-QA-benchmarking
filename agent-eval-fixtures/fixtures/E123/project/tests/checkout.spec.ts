import { expect, test } from '@playwright/test';
import { CheckoutPage } from '../pages/CheckoutPage';

test.describe('Checkout flow', () => {
  test('valid customer can complete checkout', async ({ page }) => {
    const checkout = new CheckoutPage(page);
    await checkout.startCheckout();
    await checkout.fillShippingInfo('Ada', 'Lovelace', '90210');
    await checkout.continueToOverview();
    await checkout.finishOrder();
    await checkout.expectComplete();
  });

  test('missing postal code shows validation error', async ({ page }) => {
    const checkout = new CheckoutPage(page);
    await checkout.startCheckout();
    await checkout.fillShippingInfo('Ada', 'Lovelace', '');
    await page.getByRole('button', { name: 'Continue' }).click();
    await expect(page.getByText('Postal Code is required')).toBeVisible();
  });

  test('cancel returns from overview to cart', async ({ page }) => {
    const checkout = new CheckoutPage(page);
    await checkout.startCheckout();
    await checkout.fillShippingInfo('Ada', 'Lovelace', '90210');
    await checkout.continueToOverview();
    await page.getByRole('button', { name: 'Cancel' }).click();
    await expect(page).toHaveURL(/cart/);
  });
});
