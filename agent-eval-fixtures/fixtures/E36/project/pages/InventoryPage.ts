import { expect, Page } from '@playwright/test';

export class InventoryPage {
  readonly page: Page;
  readonly productTitle;
  readonly sortDropdown;
  readonly cartBadge;
  readonly cartLink;
  readonly menuButton;
  readonly logoutButton;

  constructor(page: Page) {
    this.page = page;
    this.productTitle = page.locator('.title');
    this.sortDropdown = page.locator('[data-test="product-sort-container"]');
    this.cartBadge = page.locator('.shopping_cart_badge');
    this.cartLink = page.locator('[data-test="shopping-cart-link"]');
    this.menuButton = page.locator('[data-test="react-burger-menu-btn"]');
    this.logoutButton = page.locator('[data-test="logout-sidebar-link"]');
  }

  async assertOnInventoryPage() {
    await expect(this.productTitle).toContainText('Products');
    // Wait for inventory items to be loaded
    await this.page.waitForSelector('.inventory_item', { state: 'attached' });
  }

  getAddToCartButton(productId: string) {
    return this.page.locator(`[data-test="add-cart-${productId}"]`);
  }

  getRemoveButton(productId: string) {
    return this.page.locator(`[data-test="remove-${productId}"]`);
  }

  async addProductToCart(productId: string) {
    await this.getAddToCartButton(productId).click();
  }

  async removeProductFromCart(productId: string) {
    await this.getRemoveButton(productId).click();
  }

  async getCartItemCount() {
    const badge = this.cartBadge.first();
    const count = await badge.count();
    if (count === 0) return 0;
    const text = await badge.textContent();
    return text ? parseInt(text) : 0;
  }

  async assertCartItemCount(count: number) {
    if (count === 0) {
      await expect(this.cartBadge).toHaveCount(0);
    } else {
      await expect(this.cartBadge).toContainText(count.toString());
    }
  }

  async goToCart() {
    await this.cartLink.click();
  }

  async sortProducts(option: string) {
    await this.sortDropdown.selectOption(option);
  }

  async getProductNames() {
    const names = await this.page.locator('.inventory_item_name').allTextContents();
    return names;
  }

  async getProductPrices() {
    const prices = await this.page.locator('.inventory_item_price').allTextContents();
    return prices.map(p => parseFloat(p.replace('$', '')));
  }

  async openMenu() {
    await this.menuButton.click();
    // Wait for sidebar to be visible
    await this.page.locator('.bm-menu-wrap').waitFor({ state: 'visible' });
  }

  async logout() {
    await this.openMenu();
    await this.logoutButton.click();
  }
}
