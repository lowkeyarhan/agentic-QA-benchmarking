export class DocumentUploadScreen {
  async fillShipping(address: string): Promise<void> {
    const field = await $('~ShippingAddress');
    await field.setValue(address);
  }

  async submitOrder(): Promise<void> {
    const submit = await $('~PlaceOrder');
    await submit.waitForDisplayed({ timeout: 10_000 });
    await submit.click();
  }

  async verifyConfirmation(): Promise<void> {
    const banner = await $('~OrderConfirmed');
    await banner.waitForDisplayed({ timeout: 10_000 });
  }

  async completeDocumentUpload(): Promise<void> {
    const upload = await $('~UploadButton');
    await upload.waitForDisplayed({ timeout: 10_000 });
    await upload.click();
  }
}
