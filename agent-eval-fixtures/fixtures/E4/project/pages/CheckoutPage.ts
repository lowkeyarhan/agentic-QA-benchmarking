import { $ } from '@wdio/globals';
import { expect } from 'expect-webdriverio';

export class CheckoutPage {
  get firstNameInput() {
    return $('[data-test="firstName"]');
  }

  get lastNameInput() {
    return $('[data-test="lastName"]');
  }

  get postalCodeInput() {
    return $('[data-test="postalCode"]');
  }

  get continueButton() {
    return $('[data-test="continue"]');
  }

  get cancelButton() {
    return $('[data-test="cancel"]');
  }

  get errorMessage() {
    return $('[data-test="error"]');
  }

  async assertOnCheckoutPage() {
    await expect(browser).toHaveUrlExpect(/checkout-step-one.html/);
  }

  async fillCheckoutForm(firstName: string, lastName: string, postalCode: string) {
    await this.firstNameInput.setValue(firstName);
    await this.lastNameInput.setValue(lastName);
    await this.postalCodeInput.setValue(postalCode);
  }

  async continueCheckout() {
    await this.continueButton.click();
  }

  async cancelCheckout() {
    await this.cancelButton.click();
  }

  async assertErrorMessage(message: string) {
    await expect(this.errorMessage).toHaveText(message);
  }
}

export class CheckoutOverviewPage {
  get finishButton() {
    return $('[data-test="finish"]');
  }

  get cancelButton() {
    return $('[data-test="cancel"]');
  }

  get subtotalLabel() {
    return $('[data-test="subtotal-label"]');
  }

  get taxLabel() {
    return $('[data-test="tax-label"]');
  }

  get totalLabel() {
    return $('[data-test="total-label"]');
  }

  async assertOnOverviewPage() {
    await expect(browser).toHaveUrlExpect(/checkout-step-two.html/);
  }

  async finishOrder() {
    await this.finishButton.click();
  }

  async cancelOrder() {
    await this.cancelButton.click();
  }

  async asyncGetSubtotal() {
    const text = await this.subtotalLabel.getText();
    return text ? parseFloat(text.replace('Item total: $', '')) : 0;
  }

  async asyncGetTax() {
    const text = await this.taxLabel.getText();
    return text ? parseFloat(text.replace('Tax: $', '')) : 0;
  }

  async asyncGetTotal() {
    const text = await this.totalLabel.getText();
    return text ? parseFloat(text.replace('Total: $', '')) : 0;
  }
}

export class CheckoutCompletePage {
  get completeMessage() {
    return $('[data-test="complete-header"]');
  }

  get completeText() {
    return $('[data-test="complete-text"]');
  }

  get backHomeButton() {
    return $('[data-test="back-to-products"]');
  }

  async assertOnCompletePage() {
    await expect(browser).toHaveUrlExpect(/checkout-complete.html/);
  }

  async assertOrderComplete() {
    await expect(this.completeMessage).toHaveText('Thank you for your order!');
  }

  async backToProducts() {
    await this.backHomeButton.click();
  }
}
