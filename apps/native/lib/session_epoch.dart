/// Rejects late responses from a prior connection, including a reconnect
/// that happens to reuse the same node identifier.
class MetricsSessionEpoch {
  int _value = 0;

  int get snapshot => _value;

  int invalidate() => ++_value;

  bool accepts(int ticket) => ticket == _value;
}
