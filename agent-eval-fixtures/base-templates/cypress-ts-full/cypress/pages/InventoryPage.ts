export class InventoryPage {
  // Selectors
  readonly inventoryContainer = '[data-test="inventory-container"]';
  readonly inventoryItem = '.inventory_item';
  readonly inventoryItemName = '.inventory_item_name';
  readonly inventoryItemPrice = '.inventory_item_price';
  readonly sortDropdown = '[data-test="product-sort-container"]';
  readonly cartBadge = '.shopping_cart_badge';
  readonly cartLink = '.shopping_cart_link';
  readonly menuButton = '#react-burger-menu-btn';
  readonly menuWrap = '.bm-menu-wrap';

  assertOnInventoryPage() {
    cy.get(this.inventoryContainer).should('be.visible');
  }

  addProductToCart(productId: string) {
    cy.get(`[data-test="add-to-cart-${productId}"]`).click();
  }

  removeProductFromCart(productId: string) {
    cy.get(`[data-test="remove-${productId}"]`).click();
  }

  goToCart() {
    cy.get(this.cartLink).click();
  }

  getCartItemCount(): Cypress.Chainable<number> {
    return cy.get('body').then(($body) => {
      if ($body.find(this.cartBadge).length > 0) {
        return cy.get(this.cartBadge).invoke('text').then((text) => parseInt(text, 10));
      }
      return cy.wrap(0);
    });
  }

  assertCartItemCount(count: number) {
    if (count === 0) {
      cy.get(this.cartBadge).should('not.exist');
    } else {
      cy.get(this.cartBadge).should('have.text', count.toString());
    }
  }

  sortBy(option: 'az' | 'za' | 'lohi' | 'hilo') {
    cy.get(this.sortDropdown).select(option);
  }

  getProductNames(): Cypress.Chainable<string[]> {
    return cy.get(this.inventoryItemName).then(($items) => {
      return Cypress._.map($items, (item) => item.innerText);
    });
  }

  getProductPrices(): Cypress.Chainable<number[]> {
    return cy.get(this.inventoryItemPrice).then(($items) => {
      return Cypress._.map($items, (item) => parseFloat(item.innerText.replace('$', '')));
    });
  }

  openMenu() {
    cy.get(this.menuButton).click();
    cy.get(this.menuWrap).should('be.visible');
  }

  logout() {
    this.openMenu();
    cy.get('#logout_sidebar_link').click();
  }
}
