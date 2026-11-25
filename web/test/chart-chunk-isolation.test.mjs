import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const app = readFileSync(new URL('../src/App.tsx', import.meta.url), 'utf8');
const chart = readFileSync(new URL('../src/HostHistoryChart.tsx', import.meta.url), 'utf8');
const css = readFileSync(new URL('../src/styles.css', import.meta.url), 'utf8');

test('expensive Recharts code is loaded on demand, not at dashboard sign-in', () => {
  assert.match(app, /lazy\(\(\) => import\('\.\/HostHistoryChart'\)\)/);
  assert.match(app, /<Suspense fallback=/);
  assert.match(app, /<HostHistoryChart history=\{history\} hours=\{historyHours\}\/>/);
  assert.doesNotMatch(app, /from 'recharts'/);
  assert.match(chart, /from 'recharts'/);
});

test('the extracted chart retains all three time-series and accessible labels', () => {
  assert.match(chart, /aria-label=\{'Time series chart, last ' \+ hours \+ ' hours'\}/);
  for (const series of ['cpu', 'memory', 'disk']) {
    assert.match(chart, new RegExp('dataKey="' + series + '"'));
  }
  assert.match(chart, /ResponsiveContainer width="100%" height="100%"/);
  assert.match(app, /role="status">Preparing history chart/);
  assert.match(css, /\.chart-loading\{[^}]*var\(--soft\)/);
});

test('visualization is conditional on host history and uses no privileged credentials', () => {
  assert.match(app, /history\.length \? <Suspense/);
  assert.doesNotMatch(chart, /Authorization|fetch\(|localStorage|sessionStorage/);
});
