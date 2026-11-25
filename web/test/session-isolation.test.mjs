import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import ts from 'typescript';

const source = readFileSync(new URL('../src/requestEpoch.ts', import.meta.url), 'utf8');
const compiled = ts.transpileModule(source, {
  compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ESNext }
}).outputText;
const { RequestEpoch } = await import(
  'data:text/javascript;base64,' + Buffer.from(compiled).toString('base64')
);

test('a response from an old administrator session cannot be accepted', async () => {
  const session = new RequestEpoch();
  const first = session.snapshot();
  let applied = 'none';
  const stale = Promise.resolve().then(() => {
    if (session.accepts(first)) applied = 'previous session data';
  });
  session.invalidate(); // owner disconnects and starts another session
  const second = session.snapshot();
  await stale;
  assert.equal(applied, 'none');
  assert.equal(session.accepts(first), false);
  assert.equal(session.accepts(second), true);
});

test('out-of-order polls cannot replace newer host snapshots', async () => {
  const polls = new RequestEpoch();
  const oldRequest = polls.begin();
  const newestRequest = polls.begin();
  assert.equal(polls.accepts(oldRequest), false);
  assert.equal(polls.accepts(newestRequest), true);
  polls.invalidate();
  assert.equal(polls.accepts(newestRequest), false);
});

test('disconnect and reconnect guard refresh, delayed CSV and reset all private state', () => {
  const app = readFileSync(new URL('../src/App.tsx', import.meta.url), 'utf8');
  assert.match(app, /const session = useRef\(new RequestEpoch\(\)\)/);
  assert.match(app, /const polling = useRef\(new RequestEpoch\(\)\)/);
  assert.match(app, /if \(!stillCurrent\(\)\) return/);
  assert.match(app, /if \(stillCurrent\(\)\) setError/);
  assert.match(app, /if \(stillCurrent\(\)\) setLoading\(false\)/);
  assert.match(app, /if \(!session\.current\.accepts\(sessionTicket\)\) return/);
  assert.match(app, /function disconnect\(\)[\s\S]*?session\.current\.invalidate\(\)/);
  assert.match(app, /function disconnect\(\)[\s\S]*?setExportBusy\(false\)/);
  assert.match(app, /onClick=\{disconnect\}>Reconnect/);
  assert.match(app, /onClick=\{disconnect\}><LogOut/);
  assert.doesNotMatch(app, /localStorage|sessionStorage/);
});
