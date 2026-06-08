import { InventoryPage } from '../pages/InventoryPage';
import { LoginPage } from '../pages/LoginPage';

describe('@sorting Product Sorting Tests', () => {
  const loginPage = new LoginPage();
  const inventoryPage = new InventoryPage();

  beforeEach(() => {
    loginPage.visit();
    loginPage.login('standard_user', 'secret_sauce');
  });

  it('@test_type:regression Sort dropdown is visible', () => {
    cy.get('[data-test="product-sort-container"]').should('be.visible');
  });

  it('@test_type:regression Default sort is A to Z', () => {
    cy.get('[data-test="product-sort-container"]').should('have.value', 'az');
  });

  it('@test_type:regression Can sort products A to Z', () => {
    inventoryPage.sortBy('az');
    inventoryPage.getProductNames().then((names) => {
      const sorted = [...names].sort();
      expect(names).to.deep.equal(sorted);
    });
  });

  it('@test_type:regression Can sort products Z to A', () => {
    inventoryPage.sortBy('za');
    inventoryPage.getProductNames().then((names) => {
      const sorted = [...names].sort().reverse();
      expect(names).to.deep.equal(sorted);
    });
  });

  it('@smoke @test_type:regression Can sort products by price low to high', () => {
    inventoryPage.sortBy('lohi');
    inventoryPage.getProductPrices().then((prices) => {
      const sorted = [...prices].sort((a, b) => a - b);
      expect(prices).to.deep.equal(sorted);
    });
  });

  it('@test_type:regression Can sort products by price high to low', () => {
    inventoryPage.sortBy('hilo');
    inventoryPage.getProductPrices().then((prices) => {
      const sorted = [...prices].sort((a, b) => b - a);
      expect(prices).to.deep.equal(sorted);
    });
  });

  it('@test_type:regression Sort persists after adding item to cart', () => {
    inventoryPage.sortBy('hilo');
    inventoryPage.addProductToCart('sauce-labs-fleece-jacket');
    cy.get('[data-test="product-sort-container"]').should('have.value', 'hilo');
  });
});
