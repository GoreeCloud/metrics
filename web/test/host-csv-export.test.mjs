import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import ts from 'typescript';

const source = readFileSync(new URL('../src/hostExport.ts', import.meta.url), 'utf8');
const compiled = ts.transpileModule(source, {
  compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ESNext }
}).outputText;
const { fetchHostCsv } = await import('data:text/javascript;base64,' + Buffer.from(compiled).toString('base64'));

test('CSV export is explicit, authenticated, redirect-denying and memory bounded', async () => {
  const fetcher = async (url, options) => {
    assert.equal(url, '/api/v1/systems/host-1/export.csv?hours=24&limit=10000');
    assert.equal(options.headers.Authorization, 'Bearer dummy-private-secret');
    assert.equal(options.redirect, 'error');
    assert.equal(options.cache, 'no-store');
    assert.equal(options.credentials, 'omit');
    assert.equal(options.referrerPolicy, 'no-referrer');
    return new Response('id,node_id\n1,host-1\n', {
      status: 200, headers: { 'content-type': 'text/csv; charset=utf-8', 'x-next-before-id': '123' }
    });
  };
  const result = await fetchHostCsv('host-1', 'dummy-private-secret', 24, fetcher);
  assert.equal(result.partial, true);
  assert.equal(await result.blob.text(), 'id,node_id\n1,host-1\n');
});

test('complete page is distinguished from a truncated export', async () => {
  const response = new Response('id\n', { headers: { 'content-type': 'text/csv' } });
  const result = await fetchHostCsv('host-a', 'a', 6, async () => response);
  assert.equal(result.partial, false);
  assert.equal(await result.blob.text(), 'id\n');
});

test('rejects oversized responses before and during streaming', async () => {
  await assert.rejects(fetchHostCsv('host-a', 'a', 168, async () => new Response('x', {
    headers: { 'content-type': 'text/csv', 'content-length': String(9 * 1024 * 1024) }
  })), /size limit/);
  const tooLarge = new ReadableStream({
    start(controller) {
      controller.enqueue(new Uint8Array(8 * 1024 * 1024 + 1));
      controller.close();
    }
  });
  await assert.rejects(fetchHostCsv('host-a', 'a', 24, async () => new Response(tooLarge, {
    headers: { 'content-type': 'text/csv' }
  })), /size limit/);
});

test('rejects invalid host, hours, content-type and pagination cursor', async () => {
  const unreachable = () => { throw Error('fetch must not be invoked'); };
  await assert.rejects(fetchHostCsv('../other', 'a', 24, unreachable), /host identifier/);
  await assert.rejects(fetchHostCsv('host-a', 'a', 0, unreachable), /time window/);
  await assert.rejects(fetchHostCsv('host-a', 'a', 24, async () => new Response('oops')), /content type/);
  await assert.rejects(fetchHostCsv('host-a', 'a', 24, async () => new Response('x', {
    headers: { 'content-type': 'text/csv', 'x-next-before-id': '1;evil' }
  })), /pagination cursor/);
});

test('HTTP authentication failures redact bearer secret', async () => {
  await assert.rejects(fetchHostCsv('host-a', 'very-secret-token', 24,
    async () => new Response('', { status: 401 })
  ), (err) => err instanceof Error && err.message === 'Administrator authentication failed' &&
    !err.message.includes('very-secret-token'));
});

test('web export stays owner initiated and never writes persistent token storage', () => {
  const app = readFileSync(new URL('../src/App.tsx', import.meta.url), 'utf8');
  assert.match(app, /onClick=\{\(\) => void downloadCsv\(\)\}/);
  assert.match(app, /disabled=\{exportBusy\}/);
  assert.match(app, /download = 'metrics-'/);
  assert.match(app, /URL\.revokeObjectURL/);
  assert.doesNotMatch(app, /localStorage|sessionStorage/);
  assert.match(app, /Older pages require the API cursor/);
});
