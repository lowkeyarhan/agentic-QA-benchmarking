import { CartPage } from '../pages/CartPage';
import { CheckoutPage } from '../pages/CheckoutPage';
import { InventoryPage } from '../pages/InventoryPage';
import { LoginPage } from '../pages/LoginPage';

describe('@checkout Checkout Flow Tests', () => {
  const loginPage = new LoginPage();
  const inventoryPage = new InventoryPage();
  const cartPage = new CartPage();
  const checkoutPage = new CheckoutPage();

  beforeEach(() => {
    loginPage.visit();
    loginPage.login('standard_user', 'secret_sauce');
    inventoryPage.addProductToCart('sauce-labs-backpack');
    inventoryPage.goToCart();
    cartPage.goToCheckout();
  });

  describe('Checkout Information Step', () => {
    it('@test_type:regression Checkout requires first name', () => {
      checkoutPage.fillCheckoutForm('', 'Doe', '12345');
      checkoutPage.continueCheckout();
      checkoutPage.assertErrorMessage('First Name is required');
    });

    it('@test_type:regression Checkout requires last name', () => {
      checkoutPage.fillCheckoutForm('John', '', '12345');
      checkoutPage.continueCheckout();
      checkoutPage.assertErrorMessage('Last Name is required');
    });

    it('@test_type:regression Checkout requires postal code', () => {
      checkoutPage.fillCheckoutForm('John', 'Doe', '');
      checkoutPage.continueCheckout();
      checkoutPage.assertErrorMessage('Postal Code is required');
    });

    it('@smoke @test_type:regression Valid form proceeds to overview', () => {
      checkoutPage.fillCheckoutForm('John', 'Doe', '12345');
      checkoutPage.continueCheckout();
      checkoutPage.assertOnOverviewPage();
    });

    it('@test_type:regression Cancel returns to cart', () => {
      checkoutPage.cancelCheckout();
      cy.url().should('include', 'cart.html');
    });
  });

  describe('Checkout Overview Step', () => {
    beforeEach(() => {
      checkoutPage.fillCheckoutForm('John', 'Doe', '12345');
      checkoutPage.continueCheckout();
    });

    it('@test_type:regression Overview displays correct item', () => {
      cy.get('.inventory_item_name').should('contain.text', 'Sauce Labs Backpack');
    });

    it('@test_type:regression Overview displays payment information', () => {
      cy.get('[data-test="payment-info-value"]').should('contain.text', 'SauceCard');
    });

    it('@test_type:regression Overview displays shipping information', () => {
      cy.get('[data-test="shipping-info-value"]').should('contain.text', 'Free Pony Express Delivery');
    });

    it('@test_type:regression Overview calculates correct subtotal', () => {
      checkoutPage.getSubtotal().should('eq', 29.99);
    });

    it('@test_type:regression Overview calculates tax', () => {
      checkoutPage.getTax().should('be.gt', 0);
    });

    it('@test_type:regression Overview calculates total correctly', () => {
      checkoutPage.getSubtotal().then((subtotal) => {
        checkoutPage.getTax().then((tax) => {
          checkoutPage.getTotal().should('be.closeTo', subtotal + tax, 0.01);
        });
      });
    });

    it('@smoke @test_type:regression Finish completes the order', () => {
      checkoutPage.finishOrder();
      checkoutPage.assertOnCompletePage();
    });

    it('@test_type:regression Cancel returns to inventory', () => {
      checkoutPage.cancelOrder();
      inventoryPage.assertOnInventoryPage();
    });
  });

  describe('Checkout Complete Step', () => {
    beforeEach(() => {
      checkoutPage.fillCheckoutForm('John', 'Doe', '12345');
      checkoutPage.continueCheckout();
      checkoutPage.finishOrder();
    });

    it('@smoke @test_type:regression Complete page shows success message', () => {
      checkoutPage.assertOrderComplete();
    });

    it('@test_type:regression Complete page shows dispatch message', () => {
      cy.get('[data-test="complete-text"]').should('contain.text', 'dispatched');
    });

    it('@test_type:regression Back to products returns to inventory', () => {
      checkoutPage.backToProducts();
      inventoryPage.assertOnInventoryPage();
    });

    it('@test_type:regression Cart is empty after order completion', () => {
      checkoutPage.backToProducts();
      inventoryPage.assertCartItemCount(0);
    });
  });

  describe('Full Checkout Flow', () => {
    it('@e2e @smoke @test_type:regression Complete purchase flow', () => {
      // Already on checkout from beforeEach, go back to inventory
      checkoutPage.cancelCheckout();
      cartPage.continueShopping();

      // Add another item
      inventoryPage.addProductToCart('sauce-labs-bike-light');

      // Go to checkout
      inventoryPage.goToCart();
      cartPage.goToCheckout();

      // Fill form
      checkoutPage.fillCheckoutForm('Jane', 'Smith', '54321');
      checkoutPage.continueCheckout();

      // Verify overview
      checkoutPage.assertOnOverviewPage();
      checkoutPage.getTotal().should('be.gt', 0);

      // Complete order
      checkoutPage.finishOrder();
      checkoutPage.assertOrderComplete();

      // Return to products
      checkoutPage.backToProducts();
      inventoryPage.assertOnInventoryPage();
    });
  });
});
