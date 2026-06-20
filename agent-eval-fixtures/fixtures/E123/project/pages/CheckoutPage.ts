import { expect, type Page } from '@playwright/test';

export class CheckoutPage {
  constructor(private readonly page: Page) {}

  async startCheckout() {
    await this.page.goto('/cart.html');
    await this.page.getByRole('button', { name: 'Checkout' }).click();
  }

  async fillShippingInfo(firstName: string, lastName: string, postalCode: string) {
    await this.page.getByLabel('First Name').fill(firstName);
    await this.page.getByLabel('Last Name').fill(lastName);
    await this.page.getByLabel('Postal Code').fill(postalCode);
  }

  async continueToOverview() {
    await this.page.getByRole('button', { name: 'Continue' }).click();
    await expect(this.page).toHaveURL(/checkout-step-two/);
  }

  async finishOrder() {
    await this.page.getByRole('button', { name: 'Finish' }).click();
  }

  async expectComplete() {
    await expect(this.page.getByText('Thank you for your order!')).toBeVisible();
  }
}
