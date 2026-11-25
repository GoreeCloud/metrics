"""Verify ingest request admission occurs before JSON parsing and bounds memory."""
from __future__ import annotations

import json

from fastapi.testclient import TestClient
from server.app import MAX_INGEST_BYTES, app


def configure(monkeypatch, tmp_path):
    monkeypatch.setenv("METRICS_DB_PATH", str(tmp_path / "metrics.sqlite3"))
    monkeypatch.setenv("METRICS_ADMIN_TOKEN", "a" * 40)
    monkeypatch.setenv("METRICS_AGENT_TOKENS",
                       json.dumps({"node-a": "b" * 40, "node-b": "c" * 40}))


def sample(node="node-a"):
    return {"node_id": node, "hostname": "Synthetic",
            "cpu_percent": 1, "memory_percent": 1, "disk_percent": 2,
            "memory_used_bytes": 100, "disk_used_bytes": 100,
            "rx_bytes": 0, "tx_bytes": 0, "uptime_seconds": 10}


def test_unauthorized_rejected_before_parsing(monkeypatch, tmp_path):
    configure(monkeypatch, tmp_path)
    with TestClient(app) as client:
        assert client.post("/api/v1/ingest", content=b"{invalid-json",
                           headers={"Content-Type": "application/json"}).status_code == 401
        assert client.post("/api/v1/ingest", content=b"x" * (MAX_INGEST_BYTES + 8),
                           headers={"Content-Type": "application/json"}).status_code == 401
        # A credential authorized for a different node does not authorize it.
        result = client.post("/api/v1/ingest", json=sample("node-b"),
                             headers={"X-Agent-Token": "b" * 40})
        assert result.status_code == 401
        assert client.get("/api/v1/systems").status_code == 401


def test_authenticated_limits_and_valid_sample(monkeypatch, tmp_path):
    configure(monkeypatch, tmp_path)
    token = {"X-Agent-Token": "b" * 40}
    with TestClient(app) as client:
        response = client.post("/api/v1/ingest",
                               content=b"z" * (MAX_INGEST_BYTES + 1),
                               headers=token | {"Content-Type": "application/json"})
        assert response.status_code == 413
        assert response.headers["cache-control"] == "no-store"
        assert client.post("/api/v1/ingest", content=b"{}",
                           headers=token | {"Content-Type": "text/plain"}).status_code == 415
        assert client.post("/api/v1/ingest", json=sample(), headers=token).status_code == 202
        assert client.post("/api/v1/ingest", json=sample(),
                           headers={"X-Agent-Token": "not-a-real-token"}).status_code == 401


def test_streaming_chunked_body_is_bounded(monkeypatch, tmp_path):
    configure(monkeypatch, tmp_path)
    chunks = [b" " * 8192 for _ in range((MAX_INGEST_BYTES // 8192) + 1)]
    with TestClient(app) as client:
        def source():
            yield from chunks
        response = client.post("/api/v1/ingest", content=source(),
                               headers={"X-Agent-Token": "b" * 40,
                                        "Content-Type": "application/json",
                                        "Transfer-Encoding": "chunked"})
        assert response.status_code == 413
