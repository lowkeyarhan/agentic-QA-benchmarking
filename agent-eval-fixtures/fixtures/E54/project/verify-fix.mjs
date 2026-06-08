// Simple verification script to check if selectors are correct
// Read the TypeScript file directly and check the values
import { readFileSync } from 'fs';

const content = readFileSync('./src/inventory.ts', 'utf-8');

let passed = 0;
let failed = 0;

// Test 1: Check if addToCartButton contains 'add-to-cart'
const addToCartMatch = content.match(/addToCartButton:\s*'([^']+)'/);
if (addToCartMatch) {
  const selector = addToCartMatch[1];
  if (selector.includes('add-to-cart')) {
    console.log('✓ Test 1 passed: addToCartButton contains "add-to-cart"');
    console.log(`  Selector: ${selector}`);
    passed++;
  } else {
    console.log('✗ Test 1 failed: addToCartButton should contain "add-to-cart"');
    console.log(`  Expected to contain: add-to-cart`);
    console.log(`  Received: ${selector}`);
    failed++;
  }
} else {
  console.log('✗ Test 1 failed: Could not find addToCartButton selector');
  failed++;
}

// Test 2: Check if productName is '.inventory_item_name'
const productNameMatch = content.match(/productName:\s*'([^']+)'/);
if (productNameMatch) {
  const selector = productNameMatch[1];
  if (selector === '.inventory_item_name') {
    console.log('✓ Test 2 passed: productName is ".inventory_item_name"');
    console.log(`  Selector: ${selector}`);
    passed++;
  } else {
    console.log('✗ Test 2 failed: productName should be ".inventory_item_name"');
    console.log(`  Expected: .inventory_item_name`);
    console.log(`  Received: ${selector}`);
    failed++;
  }
} else {
  console.log('✗ Test 2 failed: Could not find productName selector');
  failed++;
}

console.log(`\nResults: ${passed} passed, ${failed} failed`);
process.exit(failed > 0 ? 1 : 0);
