import { InventoryPage } from '../pages/InventoryPage';
import { LoginPage } from '../pages/LoginPage';

describe('@inventory Inventory Page Tests', () => {
  const loginPage = new LoginPage();
  const inventoryPage = new InventoryPage();

  beforeEach(() => {
    loginPage.visit();
    loginPage.login('standard_user', 'secret_sauce');
  });

  it('@smoke @test_type:regression Inventory page displays 6 products', () => {
    cy.get('.inventory_item').should('have.length', 6);
  });

  it('@test_type:regression Each product has name, description, and price', () => {
    cy.get('.inventory_item').each(($item) => {
      cy.wrap($item).find('.inventory_item_name').should('be.visible');
      cy.wrap($item).find('.inventory_item_desc').should('be.visible');
      cy.wrap($item).find('.inventory_item_price').should('be.visible');
    });
  });

  it('@test_type:regression Each product has an image', () => {
    cy.get('.inventory_item_img img').should('have.length', 6);
  });

  it('@test_type:regression Can add product to cart from inventory', () => {
    inventoryPage.addProductToCart('sauce-labs-backpack');
    inventoryPage.assertCartItemCount(1);
  });

  it('@test_type:regression Can remove product from inventory page', () => {
    inventoryPage.addProductToCart('sauce-labs-backpack');
    inventoryPage.assertCartItemCount(1);
    inventoryPage.removeProductFromCart('sauce-labs-backpack');
    inventoryPage.assertCartItemCount(0);
  });

  it('@test_type:regression Add to cart button changes to Remove after adding', () => {
    cy.get('[data-test="add-to-cart-sauce-labs-backpack"]').should('be.visible');
    inventoryPage.addProductToCart('sauce-labs-backpack');
    cy.get('[data-test="remove-sauce-labs-backpack"]').should('be.visible');
  });

  it('@test_type:regression Product detail page can be accessed by clicking name', () => {
    cy.get('.inventory_item_name').first().click();
    cy.url().should('include', 'inventory-item.html');
  });

  it('@test_type:regression Product detail page can be accessed by clicking image', () => {
    cy.get('.inventory_item_img').first().click();
    cy.url().should('include', 'inventory-item.html');
  });

  it('@test_type:regression Cart link is visible', () => {
    cy.get('.shopping_cart_link').should('be.visible');
  });

  it('@test_type:regression Menu button is visible', () => {
    cy.get('#react-burger-menu-btn').should('be.visible');
  });
});
