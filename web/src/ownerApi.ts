/** Owner-only JSON transport with a bounded stream, deadline, and no redirects. */
export const MAX_OWNER_JSON_BYTES = 4 * 1024 * 1024;

export async function fetchOwnerJson(
  path: string, token: string, fetcher: typeof fetch = fetch
): Promise<unknown> {
  if (!path.startsWith('/api/v1/') || path.startsWith('//') || path.includes('#')) {
    throw new Error('Invalid owner API path');
  }
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 12000);
  try {
    const result = await fetcher(path, {
      headers: { Authorization: 'Bearer ' + token, Accept: 'application/json' },
      cache: 'no-store', redirect: 'error', credentials: 'omit',
      referrerPolicy: 'no-referrer', signal: controller.signal,
    });
    if (result.redirected) throw new Error('Unexpected API redirect');
    if (!result.ok) {
      throw new Error(result.status === 401
        ? 'Invalid administrator token' : 'API error (' + result.status + ')');
    }
    if (!/^application\/json(?:\s*;|\s*$)/i.test(result.headers.get('content-type') ?? '')) {
      throw new Error('Unexpected API content type');
    }
    const declared = result.headers.get('content-length');
    if (declared !== null && Number.isFinite(Number(declared)) &&
        Number(declared) > MAX_OWNER_JSON_BYTES) {
      throw new Error('API response exceeds size limit');
    }
    if (!result.body) throw new Error('API response has no body');
    const reader = result.body.getReader();
    const chunks: Uint8Array[] = [];
    let length = 0;
    try {
      for (;;) {
        const { done, value } = await reader.read();
        if (done) break;
        if (!value) continue;
        length += value.byteLength;
        if (length > MAX_OWNER_JSON_BYTES) {
          throw new Error('API response exceeds size limit');
        }
        chunks.push(value);
      }
    } catch (error) {
      await reader.cancel().catch(() => undefined);
      throw error;
    } finally {
      reader.releaseLock();
    }
    const bytes = new Uint8Array(length);
    let offset = 0;
    for (const chunk of chunks) {
      bytes.set(chunk, offset);
      offset += chunk.byteLength;
    }
    return JSON.parse(new TextDecoder('utf-8', { fatal: true }).decode(bytes));
  } finally {
    clearTimeout(timeout);
  }
}
