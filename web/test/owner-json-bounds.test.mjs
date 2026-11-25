import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import ts from 'typescript';

const source = readFileSync(new URL('../src/ownerApi.ts', import.meta.url), 'utf8');
const compiled = ts.transpileModule(source, {
  compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ESNext }
}).outputText;
const { fetchOwnerJson, MAX_OWNER_JSON_BYTES } = await import(
  'data:text/javascript;base64,' + Buffer.from(compiled).toString('base64')
);

test('authorized API JSON has bounded, credential-safe network options', async () => {
  const transport = async (path, options) => {
    assert.equal(path, '/api/v1/systems');
    assert.equal(options.headers.Authorization, 'Bearer synthetic-token');
    assert.equal(options.headers.Accept, 'application/json');
    assert.equal(options.cache, 'no-store');
    assert.equal(options.redirect, 'error');
    assert.equal(options.credentials, 'omit');
    assert.equal(options.referrerPolicy, 'no-referrer');
    assert.equal(typeof options.signal?.aborted, 'boolean');
    return new Response(JSON.stringify({ systems: [{ node_id: 'synthetic' }] }), {
      headers: { 'content-type': 'application/json; charset=utf-8' },
    });
  };
  assert.deepEqual(await fetchOwnerJson('/api/v1/systems', 'synthetic-token', transport),
    { systems: [{ node_id: 'synthetic' }] });
});

test('oversized response is rejected via Content-Length before body read', async () => {
  const stream = new ReadableStream({
    pull() { throw Error('content should never be read'); },
  });
  await assert.rejects(fetchOwnerJson('/api/v1/systems', 't', async () =>
    new Response(stream, { headers: {
      'content-type': 'application/json',
      'content-length': String(MAX_OWNER_JSON_BYTES + 1),
    }})), /size limit/);
});

test('streamed responses cannot evade the 4 MiB cap by omitting Content-Length', async () => {
  const stream = new ReadableStream({
    start(controller) {
      controller.enqueue(new Uint8Array(MAX_OWNER_JSON_BYTES + 1));
      controller.close();
    }
  });
  await assert.rejects(fetchOwnerJson('/api/v1/systems', 't', async () =>
    new Response(stream, { headers: { 'content-type': 'application/json' } })), /size limit/);
});

test('unexpected content-type, redirect, and authorization errors fail closed', async () => {
  await assert.rejects(fetchOwnerJson('/api/v1/systems', 'secret', async () =>
    new Response('<html>x</html>', { headers: {'content-type':'text/html'}})
  ), /content type/);
  const redirected = new Response('{}', { headers: {'content-type':'application/json'} });
  Object.defineProperty(redirected, 'redirected', { value: true });
  await assert.rejects(fetchOwnerJson('/api/v1/systems', 'secret', async () => redirected), /redirect/);
  await assert.rejects(fetchOwnerJson('/api/v1/systems', 'secret', async () =>
    new Response('hidden', { status: 401 })
  ), error => error instanceof Error && error.message === 'Invalid administrator token' &&
    !error.message.includes('secret'));
});

test('invalid API paths, malformed JSON, empty bodies, and invalid UTF-8 are refused', async () => {
  const unused = async () => { throw Error('unexpected network request'); };
  await assert.rejects(fetchOwnerJson('https://evil.invalid', 't', unused), /API path/);
  await assert.rejects(fetchOwnerJson('//evil.invalid/api/v1/a', 't', unused), /API path/);
  await assert.rejects(fetchOwnerJson('/api/v1/foo#token', 't', unused), /API path/);
  await assert.rejects(fetchOwnerJson('/api/v1/foo', 't', async () =>
    new Response('{invalid', { headers:{'content-type':'application/json'}})
  ), SyntaxError);
  await assert.rejects(fetchOwnerJson('/api/v1/foo', 't', async () =>
    new Response(null, {status:200,headers:{'content-type':'application/json'}})
  ), /no body/);
  await assert.rejects(fetchOwnerJson('/api/v1/foo', 't', async () =>
    new Response(new Uint8Array([0xff]), {headers:{'content-type':'application/json'}})
  ), TypeError);
});
