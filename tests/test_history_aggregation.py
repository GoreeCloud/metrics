"""High-frequency full-window history is aggregated rather than tail-truncated."""
from __future__ import annotations

import json
import time
from fastapi.testclient import TestClient
from server.app import app, db


def test_full_window_aggregation_includes_oldest_and_newest(monkeypatch, tmp_path):
    monkeypatch.setenv("METRICS_DB_PATH", str(tmp_path / "history.sqlite3"))
    monkeypatch.setenv("METRICS_ADMIN_TOKEN", "a" * 48)
    monkeypatch.setenv("METRICS_AGENT_TOKENS", json.dumps({"host-a": "b" * 48}))
    now = int(time.time())
    first = now - 80_001
    count = 8_000
    with TestClient(app) as client:
        with db() as connection:
            connection.execute(
                "INSERT INTO systems(node_id,hostname,first_seen,last_seen) VALUES(?,?,?,?)",
                ("host-a", "Synthetic", first, now))
            connection.executemany(
                """INSERT INTO samples(
                node_id,ts,cpu,memory,disk,memory_bytes,disk_bytes,
                rx_bytes,tx_bytes,uptime_seconds) VALUES(?,?,?,?,?,?,?,?,?,?)""",
                (("host-a", first + i * 10, float(i % 100), 50., 30.,
                  2048, 4096, i, i+1, i * 10.)
                 for i in range(count)))
        bearer = {"Authorization": "Bearer " + "a" * 48}
        response = client.get("/api/v1/systems/host-a/history?hours=24", headers=bearer)
        assert response.status_code == 200, response.text
        payload = response.json()
        rows = payload["samples"]
        assert 24 < len(rows) <= 400
        assert sum(x["sample_count"] for x in rows) == count
        assert rows[0]["ts"] >= first
        assert rows[-1]["ts"] == first + (count - 1) * 10
        assert all(a["ts"] <= b["ts"] for a, b in zip(rows, rows[1:]))
        assert all(0 <= x["cpu"] <= 100 for x in rows)
        assert payload["bucket_seconds"] > 1
        compact = client.get("/api/v1/systems/host-a/history?hours=24&points=24",
                             headers=bearer)
        assert compact.status_code == 200
        assert len(compact.json()["samples"]) <= 24
        assert sum(x["sample_count"] for x in compact.json()["samples"]) == count
        for query in ("points=23", "points=1001", "hours=0", "hours=169"):
            assert client.get("/api/v1/systems/host-a/history?" + query,
                              headers=bearer).status_code == 422
        assert client.get("/api/v1/systems/host-a/history").status_code == 401
        assert client.get("/api/v1/systems/missing/history",
                          headers=bearer).status_code == 404


def test_empty_registered_host_does_not_expose_other_nodes(monkeypatch, tmp_path):
    monkeypatch.setenv("METRICS_DB_PATH", str(tmp_path / "history-empty.sqlite3"))
    monkeypatch.setenv("METRICS_ADMIN_TOKEN", "a" * 48)
    monkeypatch.setenv("METRICS_AGENT_TOKENS", json.dumps({"host-b": "b" * 48}))
    now = int(time.time())
    with TestClient(app) as client:
        with db() as connection:
            connection.execute(
                "INSERT INTO systems(node_id,hostname,first_seen,last_seen) VALUES(?,?,?,?)",
                ("host-b", "Synthetic", now, now))
        result = client.get("/api/v1/systems/host-b/history",
                            headers={"Authorization": "Bearer " + "a" * 48})
        assert result.status_code == 200
        assert result.json()["samples"] == []
