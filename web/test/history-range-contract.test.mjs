import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const app = readFileSync(new URL('../src/App.tsx', import.meta.url), 'utf8');
const css = readFileSync(new URL('../src/styles.css', import.meta.url), 'utf8');

test('history chart offers supported 6h, 24h and 7d intervals with 24h as default', () => {
  assert.match(app, /useState<6 \| 24 \| 168>\(24\)/);
  assert.match(app, /\(\[6, 24, 168\] as const\)\.map/);
  assert.match(app, /aria-pressed=\{historyHours === hours\}/);
  assert.match(app, /aria-label="History time window"/);
  assert.match(app, /onClick=\{\(\) => setHistoryHours\(hours\)\}/);
});

test('a changed period triggers a bounded authenticated history request and correct labels', () => {
  assert.match(app, /history\?hours=' \+ historyHours \+ '&points=400'/);
  assert.match(app, /\[selected, request, lastRefresh, historyHours, token\]/);
  assert.match(app, /historyHours === 168 \? '7 days' : historyHours \+ ' hours'/);
  assert.match(app, /setHistory\(\[\]\)/);
});

test('history buttons use canonical semantic tokens, focus and touch targets', () => {
  assert.match(css, /\.history-period:focus-visible\{outline:3px solid var\(--focus\)/);
  assert.match(css, /\.history-period\{[^}]*min-height:44px/);
  assert.match(css, /history-period\.active\{[^}]*var\(--brand\)/);
});
