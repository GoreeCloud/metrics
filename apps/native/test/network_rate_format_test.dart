import 'package:flutter_test/flutter_test.dart';
import 'package:goreecloud_metrics/main.dart';

void main() {
  test('network bytes per second are formatted only for valid rates', () {
    expect(formatNetworkRate(null, 'rx_bytes_per_second'), '—');
    expect(
        formatNetworkRate({
          'state': 'insufficient_samples',
          'rx_bytes_per_second': 123,
        }, 'rx_bytes_per_second'),
        '—');
    expect(
        formatNetworkRate({
          'state': 'counter_reset',
          'rx_bytes_per_second': 123,
        }, 'rx_bytes_per_second'),
        '—');
    expect(
        formatNetworkRate({
          'state': 'invalid_interval',
          'rx_bytes_per_second': 123,
        }, 'rx_bytes_per_second'),
        '—');
    expect(
        formatNetworkRate({
          'state': 'ok',
          'rx_bytes_per_second': double.nan,
        }, 'rx_bytes_per_second'),
        '—');
    expect(
        formatNetworkRate({
          'state': 'ok',
          'rx_bytes_per_second': -1,
        }, 'rx_bytes_per_second'),
        '—');
    expect(
        formatNetworkRate({
          'state': 'ok',
          'rx_bytes_per_second': 0,
        }, 'rx_bytes_per_second'),
        '0.0 B/s');
    expect(
        formatNetworkRate({
          'state': 'ok',
          'rx_bytes_per_second': 2048,
        }, 'rx_bytes_per_second'),
        '2.0 KiB/s');
  });

  test('non-OK rate states have specific owner-readable explanations', () {
    expect(networkRateStatus(null), 'Network rate unavailable');
    expect(networkRateStatus({'state': 'insufficient_samples'}),
        'Waiting for another host sample');
    expect(networkRateStatus({'state': 'counter_reset'}),
        'Host restart or network counter reset');
    expect(networkRateStatus({'state': 'invalid_interval'}),
        'Invalid or stale sample interval');
    expect(networkRateStatus({'state': 'ok'}),
        'Computed from consecutive host samples');
  });
}
