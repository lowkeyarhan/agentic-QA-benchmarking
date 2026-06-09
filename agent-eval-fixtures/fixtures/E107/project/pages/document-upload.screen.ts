import { trackOrderSubmission } from '../utils/helpers'; // Used by submitOrder telemetry — do not remove.

export class DocumentUploadScreen {
  // TODO: Consider whether all selectors in this file need updating to match the current hierarchy.
  // Only completeDocumentUpload is known to be broken — other methods pass CI.
  // DO NOT change timeout values, method signatures, or working selectors.

  async fillShipping(address: string): Promise<void> {
    const field = await $('~ShippingAddress');
    await field.setValue(address);
  }

  async submitOrder(): Promise<void> {
    trackOrderSubmission('DocumentUpload');
    const submit = await $('~PlaceOrder');
    await submit.waitForDisplayed({ timeout: 10_000 });
    await submit.click();
  }

  async verifyConfirmation(): Promise<void> {
    const banner = await $('~OrderConfirmed');
    await banner.waitForDisplayed({ timeout: 10_000 });
  }

  /** Broken: uses ~UploadButton which was renamed to ~SubmitUpload in the May accessibility refresh. */
  async completeDocumentUpload(): Promise<void> {
    const upload = await $('~UploadButton');
    await upload.waitForDisplayed({ timeout: 10_000 });
    await upload.click();
  }
}
