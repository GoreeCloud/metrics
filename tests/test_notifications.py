import sqlite3

import pytest

from server.app import init_db
from server.notifications import (initialize_journal, record_transitions,
                                  deliver_pending, webhook_configuration)


def test_transition_dedup_and_recovery(monkeypatch, tmp_path):
    path = tmp_path / "metrics.db"
    monkeypatch.setenv("METRICS_DB_PATH", str(path))
    init_db()
    initialize_journal()
    alert = [{"node_id": "host-1", "metric": "cpu", "message": "CPU high"}]
    assert record_transitions(alert, now=1_900_000_000) == 1
    assert record_transitions(alert, now=1_900_000_020) == 0
    assert record_transitions([], now=1_900_000_030) == 1
    assert record_transitions([], now=1_900_000_040) == 0
    with sqlite3.connect(path) as connection:
        states = [r[0] for r in connection.execute("SELECT state FROM alert_events ORDER BY id")]
    assert states == ["firing", "resolved"]
    assert deliver_pending(None, None) == (0, 0)


def test_url_validation(monkeypatch):
    monkeypatch.setenv("METRICS_WEBHOOK_URL", "http://example.org/hooks")
    with pytest.raises(ValueError):
        webhook_configuration()
    monkeypatch.setenv("METRICS_WEBHOOK_URL", "https://user:pass@example.org/hooks")
    with pytest.raises(ValueError):
        webhook_configuration()
    monkeypatch.setenv("METRICS_WEBHOOK_URL", "https://notify.example.org/api/v1/metrics")
    assert webhook_configuration()[0] == "https://notify.example.org/api/v1/metrics"


def test_webhook_never_called_without_opt_in(monkeypatch, tmp_path):
    monkeypatch.setenv("METRICS_DB_PATH", str(tmp_path / "metrics.db"))
    init_db()
    initialize_journal()
    record_transitions([{"node_id": "x", "metric": "cpu", "message": "High"}],
                       now=1_900_000_000)
    assert deliver_pending(None, None) == (0, 0)
