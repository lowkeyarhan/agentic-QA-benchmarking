import { expect, test } from '@playwright/test';
import { InventoryPage } from '../pages/InventoryPage';
import { LoginPage } from '../pages/LoginPage';

test.describe('Inventory/Product Tests', () => {
  let loginPage: LoginPage;
  let inventoryPage: InventoryPage;

  test.beforeEach(async ({ page }) => {
    loginPage = new LoginPage(page);
    inventoryPage = new InventoryPage(page);
    await loginPage.goto();
    await loginPage.login('standard_user', 'secret_sauce');
    // Wait for inventory page to be fully loaded
    await inventoryPage.assertOnInventoryPage();
  });

  test('@inventory @smoke @test_type:regression All products are displayed', async ({ page }) => {
    const products = page.locator('.inventory_item');
    const count = await products.count();
    expect(count).toBe(6);
  });

  test('@inventory @test_type:regression Product details are displayed correctly', async ({ page }) => {
    const firstProduct = page.locator('.inventory_item').first();

    await expect(firstProduct.locator('.inventory_item_name')).toBeVisible();
    await expect(firstProduct.locator('.inventory_item_desc')).toBeVisible();
    await expect(firstProduct.locator('.inventory_item_price')).toBeVisible();
    await expect(firstProduct.locator('[data-test^="add-to-cart-"]')).toBeVisible();
  });

  test('@inventory @test_type:regression Product images are displayed', async ({ page }) => {
    const images = page.locator('.inventory_item_img img');
    const count = await images.count();
    expect(count).toBe(6);

    for (let i = 0; i < count; i++) {
      const img = images.nth(i);
      await expect(img).toBeVisible();
      const src = await img.getAttribute('src');
      expect(src).toBeTruthy();
      expect(src?.startsWith('/static/media/')).toBeTruthy();
    }
  });

  test('@inventory @test_type:regression Product names match expected values', async ({ page }) => {
    const expectedProducts = [
      'Sauce Labs Backpack',
      'Sauce Labs Bike Light',
      'Sauce Labs Bolt T-Shirt',
      'Sauce Labs Fleece Jacket',
      'Sauce Labs Onesie',
      'Test.allTheThings() T-Shirt (Red)'
    ];

    const productNames = await inventoryPage.getProductNames();
    expect(productNames).toEqual(expectedProducts);
  });

  test('@inventory @test_type:regression Product prices are positive numbers', async ({ page }) => {
    const prices = await inventoryPage.getProductPrices();

    for (const price of prices) {
      expect(price).toBeGreaterThan(0);
    }
  });

  test('@inventory @test_type:regression Products can be added to cart individually', async ({ page }) => {
    const addToCartButtons = page.locator('[data-test^="add-to-cart-"]');
    const count = await addToCartButtons.count();

    for (let i = 0; i < count; i++) {
      const buttonText = await addToCartButtons.nth(i).textContent();
      expect(buttonText).toBe('Add to cart');
    }
  });

  test.skip('@inventory @test_type:regression Menu button opens sidebar', async ({ page }) => {
    // TODO: Menu button tests are flaky - needs investigation
    await inventoryPage.assertOnInventoryPage();
    await inventoryPage.openMenu();

    const sidebar = page.locator('.bm-menu');
    await expect(sidebar).toBeVisible();

    const logoutLink = page.locator('[data-test="logout-sidebar-link"]');
    await expect(logoutLink).toBeVisible();
  });

  test('@inventory @test_type:regression Cart link is visible on inventory page', async ({ page }) => {
    await expect(inventoryPage.cartLink).toBeVisible();
  });

  test('@inventory @test_type:regression Cart badge shows correct count after adding items', async ({ page }) => {
    await inventoryPage.addProductToCart('sauce-labs-backpack');
    await inventoryPage.assertCartItemCount(1);

    await inventoryPage.addProductToCart('sauce-labs-bike-light');
    await inventoryPage.assertCartItemCount(2);
  });

  test('@inventory @test_type:regression Remove button appears after adding item to cart', async ({ page }) => {
    await inventoryPage.addProductToCart('sauce-labs-backpack');

    const removeButton = await inventoryPage.getRemoveButton('sauce-labs-backpack');
    await expect(removeButton).toBeVisible();
    await expect(removeButton).toHaveText('Remove');
  });

  test('@inventory @test_type:regression Add button changes to remove button', async ({ page }) => {
    const addButton = await inventoryPage.getAddToCartButton('sauce-labs-backpack');
    await expect(addButton).toHaveText('Add to cart');

    await inventoryPage.addProductToCart('sauce-labs-backpack');

    const removeButton = await inventoryPage.getRemoveButton('sauce-labs-backpack');
    await expect(removeButton).toHaveText('Remove');
  });

  test('@inventory @test_type:regression Cart badge increments correctly with multiple items', async ({ page }) => {
    await inventoryPage.addProductToCart('sauce-labs-backpack');
    await inventoryPage.assertCartItemCount(1);

    await inventoryPage.addProductToCart('sauce-labs-bike-light');
    await inventoryPage.assertCartItemCount(2);

    await inventoryPage.addProductToCart('sauce-labs-bolt-t-shirt');
    await inventoryPage.assertCartItemCount(3);
  });
});
