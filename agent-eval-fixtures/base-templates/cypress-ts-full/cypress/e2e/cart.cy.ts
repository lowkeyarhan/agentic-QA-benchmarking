import { CartPage } from '../pages/CartPage';
import { InventoryPage } from '../pages/InventoryPage';
import { LoginPage } from '../pages/LoginPage';

describe('@cart Shopping Cart Tests', () => {
  const loginPage = new LoginPage();
  const inventoryPage = new InventoryPage();
  const cartPage = new CartPage();

  beforeEach(() => {
    loginPage.visit();
    loginPage.login('standard_user', 'secret_sauce');
  });

  it('@smoke @test_type:regression Cart is empty initially', () => {
    inventoryPage.goToCart();
    cartPage.assertOnCartPage();
    cartPage.assertCartItemCount(0);
  });

  it('@test_type:regression Added items appear in cart', () => {
    inventoryPage.addProductToCart('sauce-labs-backpack');
    inventoryPage.goToCart();
    cartPage.assertCartItemCount(1);
    cartPage.getCartItemNames().should('include', 'Sauce Labs Backpack');
  });

  it('@test_type:regression Multiple items can be added to cart', () => {
    inventoryPage.addProductToCart('sauce-labs-backpack');
    inventoryPage.addProductToCart('sauce-labs-bike-light');
    inventoryPage.addProductToCart('sauce-labs-bolt-t-shirt');
    inventoryPage.goToCart();
    cartPage.assertCartItemCount(3);
  });

  it('@test_type:regression Items can be removed from cart', () => {
    inventoryPage.addProductToCart('sauce-labs-backpack');
    inventoryPage.goToCart();
    cartPage.assertCartItemCount(1);
    cartPage.removeCartItem(0);
    cartPage.assertCartItemCount(0);
  });

  it('@test_type:regression Cart shows correct item details', () => {
    inventoryPage.addProductToCart('sauce-labs-backpack');
    inventoryPage.goToCart();
    cy.get('.cart_item').first().within(() => {
      cy.get('.inventory_item_name').should('contain.text', 'Sauce Labs Backpack');
      cy.get('.inventory_item_desc').should('be.visible');
      cy.get('.inventory_item_price').should('contain.text', '$29.99');
    });
  });

  it('@test_type:regression Cart badge updates when items removed', () => {
    inventoryPage.addProductToCart('sauce-labs-backpack');
    inventoryPage.addProductToCart('sauce-labs-bike-light');
    inventoryPage.assertCartItemCount(2);
    inventoryPage.goToCart();
    cartPage.removeCartItem(0);
    cartPage.assertCartItemCount(1);
    cartPage.continueShopping();
    inventoryPage.assertCartItemCount(1);
  });

  it('@smoke @test_type:regression Continue shopping returns to inventory', () => {
    inventoryPage.addProductToCart('sauce-labs-backpack');
    inventoryPage.goToCart();
    cartPage.continueShopping();
    inventoryPage.assertOnInventoryPage();
  });

  it('@test_type:regression Checkout button is visible in cart', () => {
    inventoryPage.addProductToCart('sauce-labs-backpack');
    inventoryPage.goToCart();
    cy.get('[data-test="checkout"]').should('be.visible');
  });

  it('@smoke @test_type:regression Can navigate to checkout from cart', () => {
    inventoryPage.addProductToCart('sauce-labs-backpack');
    inventoryPage.goToCart();
    cartPage.goToCheckout();
    cy.url().should('include', 'checkout-step-one.html');
  });

  it('@test_type:regression Cart preserves items when navigating away and back', () => {
    inventoryPage.addProductToCart('sauce-labs-backpack');
    inventoryPage.addProductToCart('sauce-labs-bike-light');
    inventoryPage.goToCart();
    cartPage.assertCartItemCount(2);
    cartPage.continueShopping();
    inventoryPage.goToCart();
    cartPage.assertCartItemCount(2);
  });
});
