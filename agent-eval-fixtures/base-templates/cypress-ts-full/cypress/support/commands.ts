/// <reference types="cypress" />

// Custom command for login
Cypress.Commands.add('login', (username: string, password: string) => {
  cy.get('[data-test="username"]').type(username);
  cy.get('[data-test="password"]').type(password);
  cy.get('[data-test="login-button"]').click();
});

// Custom command for adding product to cart
Cypress.Commands.add('addToCart', (productId: string) => {
  cy.get(`[data-test="add-to-cart-${productId}"]`).click();
});

// Custom command for removing product from cart
Cypress.Commands.add('removeFromCart', (productId: string) => {
  cy.get(`[data-test="remove-${productId}"]`).click();
});

// Declare custom commands for TypeScript
declare global {
  namespace Cypress {
    interface Chainable {
      login(username: string, password: string): Chainable<void>;
      addToCart(productId: string): Chainable<void>;
      removeFromCart(productId: string): Chainable<void>;
    }
  }
}

export {};
