import { expect, Page } from '@playwright/test';

export class CheckoutPage {
  readonly page: Page;
  readonly firstNameInput;
  readonly lastNameInput;
  readonly postalCodeInput;
  readonly continueButton;
  readonly cancelButton;
  readonly errorMessage;

  constructor(page: Page) {
    this.page = page;
    this.firstNameInput = page.locator('[data-test="firstName"]');
    this.lastNameInput = page.locator('[data-test="lastName"]');
    this.postalCodeInput = page.locator('[data-test="postalCode"]');
    this.continueButton = page.locator('[data-test="continue"]');
    this.cancelButton = page.locator('[data-test="cancel"]');
    this.errorMessage = page.locator('[data-test="error"]');
  }

  async assertOnCheckoutPage() {
    await expect(this.page).toHaveURL(/checkout-step-one.html/);
  }

  async fillCheckoutForm(firstName: string, lastName: string, postalCode: string) {
    await this.firstNameInput.fill(firstName);
    await this.lastNameInput.fill(lastName);
    await this.postalCodeInput.fill(postalCode);
  }

  async continueCheckout() {
    await this.continueButton.click();
  }

  async cancelCheckout() {
    await this.cancelButton.click();
  }

  async assertErrorMessage(message: string) {
    await expect(this.errorMessage).toContainText(message);
  }
}

export class CheckoutOverviewPage {
  readonly page: Page;
  readonly finishButton;
  readonly cancelButton;
  readonly subtotalLabel;
  readonly taxLabel;
  readonly totalLabel;

  constructor(page: Page) {
    this.page = page;
    this.finishButton = page.locator('[data-test="finish"]');
    this.cancelButton = page.locator('[data-test="cancel"]');
    this.subtotalLabel = page.locator('[data-test="subtotal-label"]');
    this.taxLabel = page.locator('[data-test="tax-label"]');
    this.totalLabel = page.locator('[data-test="total-label"]');
  }

  async assertOnOverviewPage() {
    await expect(this.page).toHaveURL(/checkout-step-two.html/);
  }

  async finishOrder() {
    await this.finishButton.click();
  }

  async cancelOrder() {
    await this.cancelButton.click();
  }

  async asyncGetSubtotal() {
    const text = await this.subtotalLabel.textContent();
    return text ? parseFloat(text.replace('Item total: $', '')) : 0;
  }

  async asyncGetTax() {
    const text = await this.taxLabel.textContent();
    return text ? parseFloat(text.replace('Tax: $', '')) : 0;
  }

  async asyncGetTotal() {
    const text = await this.totalLabel.textContent();
    return text ? parseFloat(text.replace('Total: $', '')) : 0;
  }
}

export class CheckoutCompletePage {
  readonly page: Page;
  readonly completeMessage;
  readonly completeText;
  readonly backHomeButton;

  constructor(page: Page) {
    this.page = page;
    this.completeMessage = page.locator('[data-test="complete-header"]');
    this.completeText = page.locator('[data-test="complete-text"]');
    this.backHomeButton = page.locator('[data-test="back-to-products"]');
  }

  async assertOnCompletePage() {
    await expect(this.page).toHaveURL(/checkout-complete.html/);
  }

  async assertOrderComplete() {
    await expect(this.completeMessage).toContainText('Thank you for your order!');
  }

  async backToProducts() {
    await this.backHomeButton.click();
  }
}
