import { readFileSync } from 'fs';

const content = readFileSync('./src/selectors.ts', 'utf8');
const checks = [
  {
    name: 'add button selector contains add-to-cart',
    passed: /addButton:\s*'\[data-test="add-to-cart"\]'/.test(content),
  },
  {
    name: 'product name selector targets inventory item name',
    passed: /productName:\s*'\.inventory_item_name'/.test(content),
  },
];

let failures = 0;
for (const check of checks) {
  if (check.passed) {
    console.log(`PASS ${check.name}`);
  } else {
    console.log(`FAIL ${check.name}`);
    failures += 1;
  }
}

process.exit(failures > 0 ? 1 : 0);
