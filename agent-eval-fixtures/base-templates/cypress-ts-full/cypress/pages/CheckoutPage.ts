export class CheckoutPage {
  // Step One (Information)
  readonly firstNameInput = '[data-test="firstName"]';
  readonly lastNameInput = '[data-test="lastName"]';
  readonly postalCodeInput = '[data-test="postalCode"]';
  readonly continueButton = '[data-test="continue"]';
  readonly cancelButton = '[data-test="cancel"]';
  readonly errorMessage = '[data-test="error"]';

  // Step Two (Overview)
  readonly summaryInfo = '.summary_info';
  readonly summarySubtotal = '.summary_subtotal_label';
  readonly summaryTax = '.summary_tax_label';
  readonly summaryTotal = '.summary_total_label';
  readonly finishButton = '[data-test="finish"]';

  // Complete
  readonly completeHeader = '.complete-header';
  readonly completeText = '[data-test="complete-text"]';
  readonly backHomeButton = '[data-test="back-to-products"]';

  fillCheckoutForm(firstName: string, lastName: string, postalCode: string) {
    if (firstName) cy.get(this.firstNameInput).type(firstName);
    if (lastName) cy.get(this.lastNameInput).type(lastName);
    if (postalCode) cy.get(this.postalCodeInput).type(postalCode);
  }

  continueCheckout() {
    cy.get(this.continueButton).click();
  }

  cancelCheckout() {
    cy.get(this.cancelButton).click();
  }

  assertErrorMessage(message: string) {
    cy.get(this.errorMessage).should('contain.text', message);
  }

  assertOnOverviewPage() {
    cy.url().should('include', 'checkout-step-two.html');
    cy.get(this.summaryInfo).should('be.visible');
  }

  getSubtotal(): Cypress.Chainable<number> {
    return cy.get(this.summarySubtotal).invoke('text').then((text) => {
      return parseFloat(text.replace('Item total: $', ''));
    });
  }

  getTax(): Cypress.Chainable<number> {
    return cy.get(this.summaryTax).invoke('text').then((text) => {
      return parseFloat(text.replace('Tax: $', ''));
    });
  }

  getTotal(): Cypress.Chainable<number> {
    return cy.get(this.summaryTotal).invoke('text').then((text) => {
      return parseFloat(text.replace('Total: $', ''));
    });
  }

  finishOrder() {
    cy.get(this.finishButton).click();
  }

  cancelOrder() {
    cy.get(this.cancelButton).click();
  }

  assertOnCompletePage() {
    cy.url().should('include', 'checkout-complete.html');
    cy.get(this.completeHeader).should('be.visible');
  }

  assertOrderComplete() {
    cy.get(this.completeHeader).should('contain.text', 'Thank you for your order!');
  }

  backToProducts() {
    cy.get(this.backHomeButton).click();
  }
}
