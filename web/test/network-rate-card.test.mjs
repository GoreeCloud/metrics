import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';

const app = readFileSync(new URL('../src/App.tsx', import.meta.url), 'utf8');
const css = readFileSync(new URL('../src/styles.css', import.meta.url), 'utf8');

test('network-rate polling uses existing authenticated, no-store redirect-denying API helper', () => {
  const transport = readFileSync(new URL('../src/ownerApi.ts', import.meta.url), 'utf8');
  assert.match(app, /fetchOwnerJson\(path, token\)/);
  assert.match(transport, /Authorization: 'Bearer ' \+ token/);
  assert.match(transport, /redirect: 'error'/);
  assert.match(app, /request\('\/api\/v1\/systems\/' \+ host \+ '\/network-rate'\)/);
  assert.match(app, /setNetworkRate\(null\);/);
  assert.match(app, /\[selected, request, lastRefresh, historyHours, token\]/);
});

test('non-OK network rates never display a numeric rate or a misleading zero', () => {
  assert.match(app, /networkRate\.state === 'ok' \? networkRate : null/);
  assert.match(app, /'counter_reset'/);
  assert.match(app, /'invalid_interval'/);
  assert.match(app, /'insufficient_samples'/);
  assert.match(app, /rate\?\.rx_bytes_per_second == null \? '—'/);
  assert.match(app, /rate\?\.tx_bytes_per_second == null \? '—'/);
  assert.match(app, /'Counter reset or host restart'/);
});

test('network rate cards use GC UI tokens and remain responsive', () => {
  assert.match(css, /\.network-grid\{grid-template-columns:repeat\(auto-fit/);
  assert.match(css, /\.network-card \.rate-note\{[^}]*var\(--soft\)/);
});
