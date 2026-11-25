// Strict client for the authenticated, owner-held GoreeCloud Metrics API.
///
// The OS TLS verifier owns remote certificate identity. Never follow an
// HTTP(S) redirect with a privileged bearer credential.
import 'dart:convert';
import 'dart:typed_data';
import 'package:http/http.dart' as http;

const int metricsResponseLimit = 4 * 1024 * 1024;

Future<dynamic> fetchMetricsJson(
    http.Client client, Uri uri, String token) async {
  final request = http.Request('GET', uri);
  request.followRedirects = false;
  request.headers['Authorization'] = 'Bearer $token';
  request.headers['Accept'] = 'application/json';
  final response =
      await client.send(request).timeout(const Duration(seconds: 12));
  if (response.statusCode >= 300 && response.statusCode < 400) {
    throw StateError('Hub redirects are not permitted');
  }
  if (response.statusCode != 200) {
    throw StateError('Hub request failed (${response.statusCode})');
  }
  final bytes = BytesBuilder(copy: false);
  await for (final chunk
      in response.stream.timeout(const Duration(seconds: 12))) {
    if (bytes.length + chunk.length > metricsResponseLimit) {
      throw StateError('Hub response exceeds safety limit');
    }
    bytes.add(chunk);
  }
  return jsonDecode(utf8.decode(bytes.takeBytes()));
}
