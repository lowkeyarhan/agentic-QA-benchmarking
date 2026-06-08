export class CartPage {
  // Selectors
  readonly cartList = '.cart_list';
  readonly cartItem = '.cart_item';
  readonly cartItemName = '.inventory_item_name';
  readonly cartItemPrice = '.inventory_item_price';
  readonly cartQuantity = '.cart_quantity';
  readonly continueShoppingButton = '[data-test="continue-shopping"]';
  readonly checkoutButton = '[data-test="checkout"]';
  readonly removeButton = '[data-test^="remove-"]';

  assertOnCartPage() {
    cy.url().should('include', 'cart.html');
    cy.get(this.cartList).should('be.visible');
  }

  assertCartItemCount(count: number) {
    if (count === 0) {
      cy.get(this.cartItem).should('not.exist');
    } else {
      cy.get(this.cartItem).should('have.length', count);
    }
  }

  getCartItemNames(): Cypress.Chainable<string[]> {
    return cy.get(this.cartItemName).then(($items) => {
      return Cypress._.map($items, (item) => item.innerText);
    });
  }

  removeCartItem(index: number) {
    cy.get(this.removeButton).eq(index).click();
  }

  continueShopping() {
    cy.get(this.continueShoppingButton).click();
  }

  goToCheckout() {
    cy.get(this.checkoutButton).click();
  }
}
