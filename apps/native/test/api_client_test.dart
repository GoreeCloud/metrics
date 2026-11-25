import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:goreecloud_metrics/api_client.dart';

void main() {
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
