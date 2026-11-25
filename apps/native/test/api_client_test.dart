import 'dart:async';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:goreecloud_metrics/api_client.dart';

void main() {
  testEntireResponseDeadline();
  test('reads a bounded synthetic owner API JSON response', () async {
    final client = MockClient((request) async {
      expect(request.method, 'GET');
      expect(request.followRedirects, isFalse);
      expect(request.headers['Authorization'], 'Bearer secret-only-in-memory');
      expect(request.headers['Accept'], 'application/json');
      return http.Response('{"systems":[{"node_id":"synthetic"}]}', 200);
    });
    try {
      final data = await fetchMetricsJson(
          client,
          Uri.parse('https://metrics.example.test/api/v1/systems'),
          'secret-only-in-memory');
      expect(data['systems'][0]['node_id'], 'synthetic');
    } finally {
      client.close();
    }
  });

  test('rejects owner endpoint redirect without forwarding the bearer',
      () async {
    int requests = 0;
    final client = MockClient((request) async {
      requests++;
      expect(request.followRedirects, isFalse);
      return http.Response('', 307,
          headers: {'location': 'https://untrusted.example.test/steal'});
    });
    try {
      await expectLater(
        fetchMetricsJson(
            client,
            Uri.parse('https://metrics.example.test/api/v1/systems'),
            'private-token'),
        throwsA(isA<StateError>()),
      );
      expect(requests, 1);
    } finally {
      client.close();
    }
  });

  test('refuses oversized API JSON and leaves no accepted payload', () async {
    final client = MockClient((request) async =>
        http.Response('x' * (metricsResponseLimit + 1), 200));
    try {
      await expectLater(
        fetchMetricsJson(
            client,
            Uri.parse('https://metrics.example.test/api/v1/systems'),
            'private-token'),
        throwsA(isA<StateError>()),
      );
    } finally {
      client.close();
    }
  });

  test('does not silently accept unauthorized responses', () async {
    final client = MockClient((request) async => http.Response('', 401));
    try {
      await expectLater(
        fetchMetricsJson(
            client,
            Uri.parse('https://metrics.example.test/api/v1/systems'),
            'private-token'),
        throwsA(isA<StateError>()),
      );
    } finally {
      client.close();
    }
  });
}

class TrickleClient extends http.BaseClient {
  TrickleClient(this.byteStream);
  final Stream<List<int>> byteStream;

  @override
  Future<http.StreamedResponse> send(http.BaseRequest request) async {
    expect(request.followRedirects, isFalse);
    return http.StreamedResponse(byteStream, 200);
  }
}

void testEntireResponseDeadline() {
  test('native owner transport cancels a slowly trickling body', () async {
    var cancelled = false;
    Timer? source;
    final controller = StreamController<List<int>>(
      onCancel: () {
        cancelled = true;
        source?.cancel();
      },
    );
    source = Timer.periodic(const Duration(milliseconds: 8), (_) {
      controller.add([123]); // One byte well before the old 12s idle timeout.
    });
    final client = TrickleClient(controller.stream);
    try {
      await expectLater(
        fetchMetricsJson(
          client,
          Uri.parse('https://metrics.example.test/api/v1/systems'),
          'private-token',
          responseDeadline: const Duration(milliseconds: 80),
        ),
        throwsA(isA<TimeoutException>()),
      );
      expect(cancelled, isTrue);
    } finally {
      source.cancel();
      await controller.close();
      client.close();
    }
  });

  test('stream without a declared size still rejects too many bytes', () async {
    final client = TrickleClient(
      Stream.value(List<int>.filled(metricsResponseLimit + 1, 65)),
    );
    try {
      await expectLater(
        fetchMetricsJson(
          client,
          Uri.parse('https://metrics.example.test/api/v1/systems'),
          'private-token',
        ),
        throwsA(isA<StateError>()),
      );
    } finally {
      client.close();
    }
  });
}
