import { expect, test } from '@playwright/test';
import { InventoryPage } from '../pages/InventoryPage';
import { LoginPage } from '../pages/LoginPage';

test.describe('Product Sorting Tests', () => {
  let loginPage: LoginPage;
  let inventoryPage: InventoryPage;

  test.beforeEach(async ({ page }) => {
    loginPage = new LoginPage(page);
    inventoryPage = new InventoryPage(page);
    await loginPage.goto();
    await loginPage.login('standard_user', 'secret_sauce');
  });

  test('@sorting @test_type:regression Products can be sorted by name A to Z', async ({ page }) => {
    await inventoryPage.sortProducts('az');

    const productNames = await inventoryPage.getProductNames();
    const sortedNames = [...productNames].sort();

    expect(productNames).toEqual(sortedNames);
  });

  test('@sorting @test_type:regression Products can be sorted by name Z to A', async ({ page }) => {
    await inventoryPage.sortProducts('za');

    const productNames = await inventoryPage.getProductNames();
    const sortedNames = [...productNames].sort().reverse();

    expect(productNames).toEqual(sortedNames);
  });

  test('@sorting @test_type:regression Products can be sorted by price low to high', async ({ page }) => {
    await inventoryPage.sortProducts('lohi');

    const prices = await inventoryPage.getProductPrices();
    const sortedPrices = [...prices].sort((a, b) => a - b);

    expect(prices).toEqual(sortedPrices);
  });

  test('@sorting @test_type:regression Products can be sorted by price high to low', async ({ page }) => {
    await inventoryPage.sortProducts('hilo');

    const prices = await inventoryPage.getProductPrices();
    const sortedPrices = [...prices].sort((a, b) => b - a);

    expect(prices).toEqual(sortedPrices);
  });

  test('@sorting @test_type:regression Sort option persists across page elements', async ({ page }) => {
    await inventoryPage.sortProducts('za');

    const selectedValue = await inventoryPage.sortDropdown.inputValue();
    expect(selectedValue).toBe('za');
  });

  test('@sorting @test_type:regression All sort options are available', async ({ page }) => {
    const options = await inventoryPage.sortDropdown.locator('option').allTextContents();

    expect(options).toEqual([
      'Name (A to Z)',
      'Name (Z to A)',
      'Price (low to high)',
      'Price (high to low)'
    ]);
  });

  test('@sorting @test_type:regression Changing sort maintains product count', async ({ page }) => {
    const initialCount = await page.locator('.inventory_item').count();

    await inventoryPage.sortProducts('lohi');
    expect(await page.locator('.inventory_item').count()).toBe(initialCount);

    await inventoryPage.sortProducts('hilo');
    expect(await page.locator('.inventory_item').count()).toBe(initialCount);

    await inventoryPage.sortProducts('za');
    expect(await page.locator('.inventory_item').count()).toBe(initialCount);
  });
});
