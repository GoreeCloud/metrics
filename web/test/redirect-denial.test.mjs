import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

test('web API reads refuse redirects when sending administrator bearer tokens', () => {
  const source = readFileSync(resolve('src/App.tsx'), 'utf8');
  assert.match(source, /Authorization: 'Bearer ' \+ token/);
  assert.match(source, /redirect: 'error'/);
  assert.match(source, /cache: 'no-store'/);
});
