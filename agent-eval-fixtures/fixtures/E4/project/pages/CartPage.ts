import { $ } from '@wdio/globals';
import { expect } from 'expect-webdriverio';

export class CartPage {
  get cartTitle() {
    return $('.title');
  }

  get cartItems() {
    return $$('.cart_item');
  }

  get checkoutButton() {
    return $('[data-test="checkout"]');
  }

  get continueShoppingButton() {
    return $('[data-test="continue-shopping"]');
  }

  get cartBadge() {
    return $('.shopping_cart_badge');
  }

  async assertOnCartPage() {
    await expect(this.cartTitle).toHaveText('Your Cart');
  }

  async getCartItemCount() {
    return await this.cartItems.length;
  }

  async assertCartItemCount(count: number) {
    const itemCount = await this.cartItems.length;
    expect(itemCount).toBe(count);
  }

  async getCartItemNames() {
    const elements = await $$('.inventory_item_name');
    const names = [];
    for (const el of elements) {
      const text = await el.getText();
      names.push(text);
    }
    return names;
  }

  async removeCartItem(index: number) {
    const cartItems = await this.cartItems;
    const removeButton = cartItems[index].$('[data-test^="remove-"]');
    await removeButton.click();
  }

  async goToCheckout() {
    await this.checkoutButton.click();
  }

  async continueShopping() {
    await this.continueShoppingButton.click();
  }
}
