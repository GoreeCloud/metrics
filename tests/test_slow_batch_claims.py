"""Slow batches must not expire claims for later, still-unsent events."""
from __future__ import annotations

import json
import sqlite3

from server.app import init_db
from server import notifications


def test_long_batch_never_claims_unsent_work_early(monkeypatch, tmp_path):
    path = tmp_path / "synthetic-alerts.sqlite3"
    monkeypatch.setenv("METRICS_DB_PATH", str(path))
    init_db()
    notifications.initialize_journal()
    base = 2_100_000_000
    alerts = [
        {"node_id": "synthetic", "metric": f"synthetic-{i}", "message": f"Synthetic {i}"}
        for i in range(12)
    ]
    notifications.record_transitions(alerts, now=base)
    clock = [base + 1]
    monkeypatch.setattr(notifications.time, "time", lambda: clock[0])
    sent = []
    nested = []

    class Response:
        status = 204
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False

    class Opener:
        def open(self, request, timeout):
            metric = json.loads(request.data)["metric"]
            sent.append(metric)
            clock[0] += 9  # 8s request + 1s scheduling after each delivery
            if len(sent) == 8 and not nested:
                # The first worker is >60s into a slow batch; a second worker
                # must not reclaim any already-claimed, unsent member.
                nested.append(
                    notifications.deliver_pending("https://notify.example.test/events", None)
                )
            return Response()

    monkeypatch.setattr(notifications.urllib.request, "build_opener",
                        lambda *args: Opener())
    primary = notifications.deliver_pending("https://notify.example.test/events", None)
    assert primary[1] == 0
    assert nested and nested[0][1] == 0
    assert len(sent) == len(set(sent)) == 12
    assert set(sent) == {a["metric"] for a in alerts}
    assert primary[0] + nested[0][0] == 12
    with sqlite3.connect(path) as conn:
        assert conn.execute("SELECT COUNT(*) FROM alert_events WHERE sent_ts IS NOT NULL").fetchone()[0] == 12
        assert conn.execute("SELECT MIN(attempts),MAX(attempts) FROM alert_events").fetchone() == (1, 1)


def test_operator_one_shot_fails_if_delivery_fails(monkeypatch):
    monkeypatch.setattr(notifications, "_STOP", False)
    monkeypatch.setattr(notifications, "run_once", lambda: (1, 0, 1))
    monkeypatch.setattr(notifications.sys, "argv", ["notifications", "--once"])
    monkeypatch.setattr(notifications.signal, "signal", lambda *args: None)
    assert notifications.main() == 2


def test_operator_one_shot_succeeds_when_delivery_succeeds(monkeypatch):
    monkeypatch.setattr(notifications, "_STOP", False)
    monkeypatch.setattr(notifications, "run_once", lambda: (1, 1, 0))
    monkeypatch.setattr(notifications.sys, "argv", ["notifications", "--once"])
    monkeypatch.setattr(notifications.signal, "signal", lambda *args: None)
    assert notifications.main() == 0
