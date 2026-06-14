import { test, expect } from '@playwright/test';
import { DataLoader } from '../src/loader';

test.describe('Data Loader', () => {
  test('should load and return data', async () => {
    const loader = new DataLoader();

    await loader.load();

    expect(loader.getData()).toBe('loaded content');
  });
});
