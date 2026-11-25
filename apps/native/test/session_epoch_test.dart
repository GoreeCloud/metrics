import 'package:flutter_test/flutter_test.dart';
import 'package:goreecloud_metrics/session_epoch.dart';

void main() {
  test('late owner-session replies are invalidated on disconnect', () {
    final epoch = MetricsSessionEpoch();
    final firstSession = epoch.snapshot;
    expect(epoch.accepts(firstSession), isTrue);
    final secondSession = epoch.invalidate();
    expect(epoch.accepts(firstSession), isFalse);
    expect(epoch.accepts(secondSession), isTrue);
  });

  test('a second reconnect cannot accept the previous token session', () {
    final epoch = MetricsSessionEpoch();
    final connected = epoch.invalidate();
    epoch.invalidate(); // Logout
    final newConnection = epoch.invalidate();
    expect(epoch.accepts(connected), isFalse);
    expect(epoch.accepts(newConnection), isTrue);
  });
}
