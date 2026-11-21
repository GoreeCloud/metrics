"""Mock delivery, retries and refusal to execute network requests without an opt-in."""
import sqlite3

from server.app import init_db
from server import notifications


def test_success_delivery_and_no_duplicate(monkeypatch, tmp_path):
    monkeypatch.setenv("METRICS_DB_PATH", str(tmp_path / "events.db"))
    init_db()
    notifications.initialize_journal()
    notifications.record_transitions(
        [{"node_id": "host-1", "metric": "disk", "message": "At limit"}], now=2_000_000_000
    )
    called = []

    class Response:
        status = 204

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    class Opener:
        def open(self, request, timeout):
            called.append((request.get_method(), request.full_url, timeout))
            return Response()

    monkeypatch.setattr(notifications.urllib.request, "build_opener", lambda *a: Opener())
    url = "https://notify.example.test/metrics"
    assert notifications.deliver_pending(url, None, now=2_000_000_001) == (1, 0)
    assert notifications.deliver_pending(url, None, now=2_000_000_002) == (0, 0)
    assert called == [("POST", url, 8)]
    with sqlite3.connect(tmp_path / "events.db") as connection:
        assert connection.execute("SELECT sent_ts FROM alert_events").fetchone()[0] == 2_000_000_001


def test_retries_are_bounded(monkeypatch, tmp_path):
    monkeypatch.setenv("METRICS_DB_PATH", str(tmp_path / "events.db"))
    init_db()
    notifications.initialize_journal()
    notifications.record_transitions(
        [{"node_id": "host-1", "metric": "cpu", "message": "High"}], now=2_000_000_000
    )

    class Opener:
        def open(self, *args, **kwargs):
            raise OSError("Synthetic offline test")

    monkeypatch.setattr(notifications.urllib.request, "build_opener", lambda *a: Opener())
    url = "https://notify.example.test/metrics"
    assert notifications.deliver_pending(url, None, now=2_000_000_001) == (0, 1)
    assert notifications.deliver_pending(url, None, now=2_000_000_002) == (0, 0)
    with sqlite3.connect(tmp_path / "events.db") as connection:
        attempt, next_ts = connection.execute(
            "SELECT attempts,next_attempt_ts FROM alert_events"
        ).fetchone()
        assert attempt == 1 and next_ts > 2_000_000_002
