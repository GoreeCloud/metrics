"""Claim-before-IO prevents avoidable concurrent sends; expired leases recover."""
from __future__ import annotations

import sqlite3

import pytest

from server.app import init_db
from server import notifications


def pending(monkeypatch, tmp_path):
    path = tmp_path / "events.sqlite3"
    monkeypatch.setenv("METRICS_DB_PATH", str(path))
    init_db()
    notifications.initialize_journal()
    assert notifications.record_transitions(
        [{"node_id": "synthetic", "metric": "cpu", "message": "Synthetic high CPU"}],
        now=2_000_000_000,
    ) == 1
    return path


def test_concurrent_worker_cannot_claim_inflight_event(monkeypatch, tmp_path):
    path = pending(monkeypatch, tmp_path)
    posted = []

    class Response:
        status = 204
        def __enter__(self): return self
        def __exit__(self, *a): return False

    class Opener:
        def open(self, req, timeout):
            posted.append(req.data)
            # Emulate a second independent worker while the first HTTP
            # request is still in flight. This must not send the event.
            assert notifications.deliver_pending(
                "https://notify.example.test/events", None, now=2_000_000_001
            ) == (0, 0)
            return Response()

    monkeypatch.setattr(notifications.urllib.request, "build_opener",
                        lambda *args: Opener())
    assert notifications.deliver_pending(
        "https://notify.example.test/events", None, now=2_000_000_001
    ) == (1, 0)
    assert len(posted) == 1
    with sqlite3.connect(path) as conn:
        assert conn.execute(
            "SELECT attempts,sent_ts FROM alert_events"
        ).fetchone() == (1, 2_000_000_001)


def test_interrupted_send_retries_after_lease_expiry(monkeypatch, tmp_path):
    path = pending(monkeypatch, tmp_path)

    class InterruptedOpener:
        def open(self, req, timeout):
            raise KeyboardInterrupt("Synthetic process interruption")

    monkeypatch.setattr(notifications.urllib.request, "build_opener",
                        lambda *args: InterruptedOpener())
    with pytest.raises(KeyboardInterrupt):
        notifications.deliver_pending(
            "https://notify.example.test/events", None, now=2_000_000_001
        )
    with sqlite3.connect(path) as conn:
        attempt, until = conn.execute(
            "SELECT attempts,next_attempt_ts FROM alert_events"
        ).fetchone()
        assert attempt == 1
        assert until == 2_000_000_061
    # No retry while the prior worker's claim is still active.
    assert notifications.deliver_pending(
        "https://notify.example.test/events", None, now=2_000_000_010
    ) == (0, 0)

    class Response:
        status = 202
        def __enter__(self): return self
        def __exit__(self, *args): return False

    class SuccessOpener:
        def open(self, req, timeout): return Response()

    monkeypatch.setattr(notifications.urllib.request, "build_opener",
                        lambda *args: SuccessOpener())
    assert notifications.deliver_pending(
        "https://notify.example.test/events", None, now=2_000_000_062
    ) == (1, 0)
    with sqlite3.connect(path) as conn:
        assert conn.execute(
            "SELECT attempts,sent_ts FROM alert_events"
        ).fetchone() == (2, 2_000_000_062)
