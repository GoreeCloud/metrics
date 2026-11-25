// Strict client for the authenticated, owner-held GoreeCloud Metrics API.
//
// The OS TLS verifier owns remote certificate identity. Never follow an
// HTTP(S) redirect with a privileged bearer credential.
import 'dart:async';
import 'dart:convert';
import 'dart:typed_data';
import 'package:http/http.dart' as http;

const int metricsResponseLimit = 4 * 1024 * 1024;

Future<dynamic> fetchMetricsJson(http.Client client, Uri uri, String token,
    {Duration responseDeadline = const Duration(seconds: 20)}) async {
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
  if (response.contentLength != null &&
      response.contentLength! > metricsResponseLimit) {
    throw StateError('Hub response exceeds safety limit');
  }

  // Unlike Stream.timeout, this deadline is measured across the *entire*
  // response body. A peer sending one byte just before each idle timeout
  // cannot keep an administrator request alive indefinitely.
  final bytes = BytesBuilder(copy: false);
  final completed = Completer<Uint8List>();
  late final StreamSubscription<List<int>> subscription;
  subscription = response.stream.listen((chunk) {
    if (completed.isCompleted) return;
    if (bytes.length + chunk.length > metricsResponseLimit) {
      completed.completeError(StateError('Hub response exceeds safety limit'));
      scheduleMicrotask(() => unawaited(subscription.cancel()));
      return;
    }
    bytes.add(chunk);
  }, onError: (Object error, StackTrace stack) {
    if (!completed.isCompleted) completed.completeError(error, stack);
  }, onDone: () {
    if (!completed.isCompleted) completed.complete(bytes.takeBytes());
  }, cancelOnError: true);
  final deadline = Timer(responseDeadline, () {
    if (!completed.isCompleted) {
      completed
          .completeError(TimeoutException('Hub response deadline exceeded'));
      unawaited(subscription.cancel());
    }
  });

  try {
    return jsonDecode(utf8.decode(await completed.future));
  } finally {
    deadline.cancel();
    await subscription.cancel();
  }
}
