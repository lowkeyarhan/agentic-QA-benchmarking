import { expect, Page } from '@playwright/test';

export class CartPage {
  readonly page: Page;
  readonly cartTitle;
  readonly cartItems;
  readonly checkoutButton;
  readonly continueShoppingButton;
  readonly cartBadge;

  constructor(page: Page) {
    this.page = page;
    this.cartTitle = page.locator('.title');
    this.cartItems = page.locator('.cart_item');
    this.checkoutButton = page.locator('[data-test="wrong-checkout"]');
    this.continueShoppingButton = page.locator('[data-test="continue-shopping"]');
    this.cartBadge = page.locator('.shopping_cart_badge');
  }

  async assertOnCartPage() {
    await expect(this.cartTitle).toContainText('Your Cart');
  }

  async getCartItemCount() {
    return await this.cartItems.count();
  }

  async assertCartItemCount(count: number) {
    await expect(this.cartItems).toHaveCount(count);
  }

  async getCartItemNames() {
    return await this.page.locator('.inventory_item_name').allTextContents();
  }

  async removeCartItem(index: number) {
    const removeButton = this.cartItems.nth(index).locator('[data-test^="remove-"]');
    await removeButton.click();
  }

  async goToCheckout() {
    await this.checkoutButton.click();
  }

  async continueShopping() {
    await this.continueShoppingButton.click();
  }
}
