"""Counter-safe read-only per-host network rates from existing snapshots."""
from __future__ import annotations

import json
import time

from fastapi.testclient import TestClient
from server.app import app, db


def configure(monkeypatch, tmp_path):
    monkeypatch.setenv("METRICS_DB_PATH", str(tmp_path / "network.sqlite3"))
    monkeypatch.setenv("METRICS_ADMIN_TOKEN", "a" * 40)
    monkeypatch.setenv("METRICS_AGENT_TOKENS", json.dumps({"node-a": "b" * 40}))
    return {"Authorization": "Bearer " + "a" * 40}


def insert(conn, node, ts, rx, tx, uptime):
    conn.execute(
        """INSERT INTO samples(node_id,ts,cpu,memory,disk,memory_bytes,
        disk_bytes,rx_bytes,tx_bytes,uptime_seconds) VALUES (?,?,?,?,?,?,?,?,?,?)""",
        (node, ts, 10, 10, 10, 100, 100, rx, tx, uptime),
    )


def test_network_rate_real_counter_deltas_and_auth(monkeypatch, tmp_path):
    bearer = configure(monkeypatch, tmp_path)
    t = int(time.time())
    with TestClient(app) as client:
        with db() as conn:
            conn.executemany(
                "INSERT INTO systems VALUES(?,?,?,?)",
                [("node-a", "Synthetic A", t-60, t),
                 ("node-b", "Synthetic B", t-60, t)],
            )
            insert(conn, "node-a", t-60, 1000, 200, 100)
            insert(conn, "node-a", t-30, 4000, 500, 130)
            insert(conn, "node-b", t-30, 99, 99, 130)
        result = client.get("/api/v1/systems/node-a/network-rate", headers=bearer)
        assert result.status_code == 200
        value = result.json()
        assert value["state"] == "ok"
        assert value["interval_seconds"] == 30
        assert value["rx_bytes_per_second"] == 100
        assert value["tx_bytes_per_second"] == 10
        assert value["latest_ts"] == t-30
        assert "node-b" not in result.text
        assert client.get("/api/v1/systems/node-a/network-rate").status_code == 401
        assert client.get("/api/v1/systems/missing/network-rate",
                          headers=bearer).status_code == 404
        assert client.get("/api/v1/systems/INVALID/network-rate",
                          headers=bearer).status_code == 404
        assert client.get("/api/v1/systems/node-b/network-rate",
                          headers=bearer).json()["state"] == "insufficient_samples"


def test_network_rate_counter_reset_and_bad_time(monkeypatch, tmp_path):
    bearer = configure(monkeypatch, tmp_path)
    t = int(time.time())
    with TestClient(app) as client:
        with db() as conn:
            conn.execute("INSERT INTO systems VALUES(?,?,?,?)",
                         ("node-a", "Synthetic A", t-200, t))
            insert(conn, "node-a", t-120, 3000, 5000, 140)
            insert(conn, "node-a", t-100, 100, 20, 4)
        result = client.get("/api/v1/systems/node-a/network-rate", headers=bearer).json()
        assert result["state"] == "counter_reset"
        assert result["rx_bytes_per_second"] is None
        with db() as conn:
            conn.execute("UPDATE samples SET ts=? WHERE id=(SELECT MAX(id) FROM samples)",
                         (t-120,))
        assert client.get("/api/v1/systems/node-a/network-rate",
                          headers=bearer).json()["state"] == "invalid_interval"


def test_network_rate_refuses_stale_interval(monkeypatch, tmp_path):
    bearer = configure(monkeypatch, tmp_path)
    t = int(time.time())
    with TestClient(app) as client:
        with db() as conn:
            conn.execute("INSERT INTO systems VALUES(?,?,?,?)",
                         ("node-a", "Synthetic A", t-7200, t))
            insert(conn, "node-a", t-7200, 100, 100, 1)
            insert(conn, "node-a", t, 9000, 9000, 7201)
        r = client.get("/api/v1/systems/node-a/network-rate", headers=bearer)
        assert r.status_code == 200
        assert r.json()["state"] == "invalid_interval"
        assert r.json()["rx_bytes_per_second"] is None
