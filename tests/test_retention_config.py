import json
import os
import sqlite3
import time
import pytest
from fastapi.testclient import TestClient
from server.app import app, retention_days


def test_rejects_invalid_retention(monkeypatch):
    for value in ("0", "-1", "366", "xyz", "1.5"):
        monkeypatch.setenv("METRICS_RETENTION_DAYS", value)
        with pytest.raises(ValueError, match="METRICS_RETENTION_DAYS"):
            retention_days()
    monkeypatch.setenv("METRICS_RETENTION_DAYS", "14")
    assert retention_days() == 14


def test_authenticated_settings_and_ingest_pruning(tmp_path, monkeypatch):
    path = tmp_path / "metrics.db"
    monkeypatch.setenv("METRICS_DB_PATH", str(path))
    monkeypatch.setenv("METRICS_RETENTION_DAYS", "7")
    monkeypatch.setenv("METRICS_ALERT_CPU_PERCENT", "86")
    monkeypatch.setenv("METRICS_ADMIN_TOKEN", "a" * 40)
    monkeypatch.setenv("METRICS_AGENT_TOKENS", json.dumps({"host-1": "b" * 40}))
    sample = {
        "node_id": "host-1", "hostname": "Synthetic",
        "cpu_percent": 12, "memory_percent": 13, "disk_percent": 14,
        "memory_used_bytes": 0, "disk_used_bytes": 0,
        "rx_bytes": 0, "tx_bytes": 0, "uptime_seconds": 100
    }
    with TestClient(app) as client:
        assert client.get("/api/v1/config").status_code == 401
        admin = {"Authorization": "Bearer " + "a" * 40}
        data = client.get("/api/v1/config", headers=admin).json()
        assert data["retention_days"] == 7
        assert data["alert_thresholds"]["cpu_percent"] == 86
        assert "METRICS_ADMIN_TOKEN" not in str(data)
        with sqlite3.connect(path) as connection:
            connection.execute("INSERT INTO systems VALUES (?,?,?,?)",
                               ("host-1", "Synthetic", 100, 100))
            connection.execute(
                """INSERT INTO samples
                (node_id,ts,cpu,memory,disk,memory_bytes,disk_bytes,rx_bytes,tx_bytes,uptime_seconds)
                VALUES (?,?,?,?,?,?,?,?,?,?)""",
                ("host-1", int(time.time())-8*86400, 1,1,1,1,1,1,1,1)
            )
        assert client.post("/api/v1/ingest", json=sample,
                           headers={"X-Agent-Token": "b"*40}).status_code == 202
        with sqlite3.connect(path) as connection:
            assert connection.execute("SELECT COUNT(*) FROM samples").fetchone()[0] == 1
