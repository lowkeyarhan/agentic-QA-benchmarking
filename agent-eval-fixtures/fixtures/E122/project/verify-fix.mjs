import { readFileSync } from 'fs';

const source = readFileSync('./src/formatter.ts', 'utf8');

function extractFunctionBody(name) {
  const match = source.match(new RegExp(`export function ${name}[^]*?\\n}`));
  if (!match) {
    throw new Error(`Missing ${name}`);
  }
  return match[0]
    .replace(/export function /, 'function ')
    .replace(/: number/g, '')
    .replace(/: string/g, '');
}

const moduleSource = `${extractFunctionBody('formatCurrency')}\n${extractFunctionBody('formatPercent')}\nexport { formatCurrency, formatPercent };`;
const encoded = encodeURIComponent(moduleSource);
const { formatCurrency, formatPercent } = await import(`data:text/javascript,${encoded}`);

const checks = [
  ['formatCurrency', formatCurrency(12.5), '$12.50'],
  ['formatPercent', formatPercent(0.0825), '8.25%'],
];

let failures = 0;
for (const [name, received, expected] of checks) {
  if (received === expected) {
    console.log(`PASS ${name}`);
  } else {
    console.log(`FAIL ${name}`);
    console.log(`  Expected: ${expected}`);
    console.log(`  Received: ${received}`);
    failures += 1;
  }
}

process.exit(failures > 0 ? 1 : 0);
