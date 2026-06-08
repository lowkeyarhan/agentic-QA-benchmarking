import { $ } from '@wdio/globals';
import { expect } from 'expect-webdriverio';

export class InventoryPage {
  get productTitle() {
    return $('.title');
  }

  get sortDropdown() {
    return $('[data-test="product-sort-container"]');
  }

  get cartBadge() {
    return $('.shopping_cart_badge');
  }

  get cartLink() {
    return $('[data-test="shopping-cart-link"]');
  }

  get menuButton() {
    return $('[data-test="react-burger-menu-btn"]');
  }

  get logoutButton() {
    return $('[data-test="logout-sidebar-link"]');
  }

  async assertOnInventoryPage() {
    await expect(this.productTitle).toHaveText('Products');
    // Wait for inventory items to be loaded
    await $('.inventory_item').waitForExist({ timeout: 5000 });
  }

  getAddToCartButton(productId: string) {
    return $(`[data-test="add-to-cart-${productId}"]`);
  }

  getRemoveButton(productId: string) {
    return $(`[data-test="remove-${productId}"]`);
  }

  async addProductToCart(productId: string) {
    const button = this.getAddToCartButton(productId);
    await button.waitForDisplayed({ timeout: 5000 });
    await button.click();
  }

  async removeProductFromCart(productId: string) {
    await this.getRemoveButton(productId).click();
  }

  async getCartItemCount() {
    const badgeCount = await this.cartBadge.length;
    if (badgeCount === 0) return 0;
    const text = await this.cartBadge.getText();
    return text ? parseInt(text) : 0;
  }

  async assertCartItemCount(count: number) {
    if (count === 0) {
      await expect(this.cartBadge).not.toBeDisplayed();
    } else {
      await expect(this.cartBadge).toHaveText(count.toString());
    }
  }

  async goToCart() {
    await this.cartLink.click();
  }

  async sortProducts(option: string) {
    await this.sortDropdown.selectByAttribute('value', option);
  }

  async getProductNames() {
    const elements = await $$('.inventory_item_name');
    const names = [];
    for (const el of elements) {
      const text = await el.getText();
      names.push(text);
    }
    return names;
  }

  async getProductPrices() {
    const elements = await $$('.inventory_item_price');
    const prices = [];
    for (const el of elements) {
      const text = await el.getText();
      prices.push(parseFloat(text.replace('$', '')));
    }
    return prices;
  }

  async openMenu() {
    await this.menuButton.click();
    // Wait for sidebar to be visible
    await $('.bm-menu-wrap').waitForDisplayed({ timeout: 5000 });
  }

  async logout() {
    await this.openMenu();
    await this.logoutButton.click();
  }
}
