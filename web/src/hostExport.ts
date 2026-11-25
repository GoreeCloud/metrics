/** Single-page, privacy-preserving browser CSV download from the authenticated hub. */
const MAX_CSV_BYTES = 8 * 1024 * 1024;

export type HostCsvExport = { blob: Blob; partial: boolean };

export async function fetchHostCsv(
  nodeId: string, token: string, hours: number, fetcher: typeof fetch = fetch
): Promise<HostCsvExport> {
  if (!/^[a-z0-9][a-z0-9-]{0,62}$/.test(nodeId)) {
    throw new Error('Invalid host identifier');
  }
  if (!Number.isInteger(hours) || hours < 1 || hours > 168) {
    throw new Error('Invalid export time window');
  }
  const response = await fetcher(
    '/api/v1/systems/' + encodeURIComponent(nodeId) + '/export.csv?hours=' + hours + '&limit=10000',
    {
      headers: { Authorization: 'Bearer ' + token },
      cache: 'no-store', redirect: 'error', credentials: 'omit', referrerPolicy: 'no-referrer',
    }
  );
  if (response.redirected) throw new Error('Unexpected export redirect');
  if (!response.ok) throw new Error(
    response.status === 401 ? 'Administrator authentication failed' : 'CSV export failed (' + response.status + ')'
  );
  if (!(response.headers.get('content-type') || '').toLowerCase().startsWith('text/csv')) {
    throw new Error('Unexpected export content type');
  }
  const declaredLength = response.headers.get('content-length');
  if (declaredLength && Number(declaredLength) > MAX_CSV_BYTES) {
    throw new Error('CSV page exceeds local size limit');
  }
  if (!response.body) throw new Error('CSV response body unavailable');

  const reader = response.body.getReader();
  const chunks: Uint8Array<ArrayBuffer>[] = [];
  let bytes = 0;
  try {
    for (;;) {
      const { value, done } = await reader.read();
      if (done) break;
      if (!value) continue;
      bytes += value.byteLength;
      if (bytes > MAX_CSV_BYTES) throw new Error('CSV page exceeds local size limit');
      chunks.push(new Uint8Array(value));  // Copy from stream-owned buffers.
    }
  } catch (error) {
    await reader.cancel().catch(() => undefined);
    throw error;
  } finally {
    reader.releaseLock();
  }
  const cursor = response.headers.get('x-next-before-id');
  if (cursor !== null && !/^[1-9][0-9]*$/.test(cursor)) {
    throw new Error('Invalid export pagination cursor');
  }
  return { blob: new Blob(chunks, { type: 'text/csv;charset=utf-8' }), partial: cursor !== null };
}
