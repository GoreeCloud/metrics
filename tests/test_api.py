"""Authenticated API, input and ingest behavior regression tests."""
import os

os.environ["METRICS_ADMIN_TOKEN"] = "a" * 40
os.environ["METRICS_AGENT_TOKENS"] = '{"test-node":"' + "b" * 40 + '"}'

from fastapi.testclient import TestClient
from server.app import app


def sample():
    return {
        "node_id": "test-node", "hostname": "Demo host",
        "cpu_percent": 42.5, "memory_percent": 66, "disk_percent": 71,
        "memory_used_bytes": 1024, "disk_used_bytes": 2048,
        "rx_bytes": 3000, "tx_bytes": 4000, "uptime_seconds": 900,
    }


def test_authorization_and_history(tmp_path, monkeypatch):
    monkeypatch.setenv("METRICS_DB_PATH", str(tmp_path / "metrics.db"))
    with TestClient(app) as client:
        assert client.get("/healthz").status_code == 200
        assert client.get("/api/v1/systems").status_code == 401
        assert client.post("/api/v1/ingest", json=sample()).status_code == 401
        assert client.post("/api/v1/ingest", json=sample(),
                           headers={"X-Agent-Token": "b" * 40}).status_code == 202
        admin = {"Authorization": "Bearer " + "a" * 40}
        response = client.get("/api/v1/systems", headers=admin)
        assert response.status_code == 200
        assert response.json()["systems"][0]["cpu"] == 42.5
        history = client.get("/api/v1/systems/test-node/history", headers=admin)
        assert len(history.json()["samples"]) == 1
        assert "goreecloud_host_cpu_percent" in client.get("/api/v1/metrics", headers=admin).text
        assert client.post("/api/v1/ingest", json=sample(),
                           headers={"X-Agent-Token": "b" * 40}).status_code == 429


def test_invalid_input_and_node_access(tmp_path, monkeypatch):
    monkeypatch.setenv("METRICS_DB_PATH", str(tmp_path / "metrics.db"))
    with TestClient(app) as client:
        bad = sample() | {"cpu_percent": 110}
        assert client.post("/api/v1/ingest", json=bad,
                           headers={"X-Agent-Token": "b" * 40}).status_code == 422
        unknown = sample() | {"node_id": "unregistered"}
        assert client.post("/api/v1/ingest", json=unknown,
                           headers={"X-Agent-Token": "b" * 40}).status_code == 401
        admin = {"Authorization": "Bearer " + "a" * 40}
        assert client.get("/api/v1/systems/missing/history", headers=admin).status_code == 404


def test_secure_config(monkeypatch):
    from server.app import config
    monkeypatch.setenv("METRICS_ADMIN_TOKEN", "short")
    try:
        config()
        assert False, "Weak secret should fail"
    except RuntimeError:
        pass
