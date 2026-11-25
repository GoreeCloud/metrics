"""Online-compatible agent token rotation, identity separation and fail-closed config."""
from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient
from server import app as metrics


def data():
    return {"node_id": "node-a", "hostname": "Synthetic",
            "cpu_percent": 4, "memory_percent": 9, "disk_percent": 10,
            "memory_used_bytes": 12, "disk_used_bytes": 14,
            "rx_bytes": 0, "tx_bytes": 0, "uptime_seconds": 20}


def setup(monkeypatch, tmp_path, mapping):
    monkeypatch.setenv("METRICS_DB_PATH", str(tmp_path / "metrics.sqlite3"))
    monkeypatch.setenv("METRICS_ADMIN_TOKEN", "a" * 40)
    monkeypatch.setenv("METRICS_AGENT_TOKENS", json.dumps(mapping))
    monkeypatch.delenv("METRICS_STATUS_TOKEN", raising=False)


def test_backward_compatible_legacy_token_and_rotation(monkeypatch, tmp_path):
    setup(monkeypatch, tmp_path, {"node-a": "b" * 40})
    admin, agents = metrics.config()
    assert agents == {"node-a": ("b" * 40,)}
    assert admin == "a" * 40
    setup(monkeypatch, tmp_path, {"node-a": ["b" * 40, "c" * 40]})
    with TestClient(metrics.app) as client:
        assert client.post("/api/v1/ingest", json=data(),
                           headers={"X-Agent-Token": "b" * 40}).status_code == 202
        # Both keys validate the same node, but pacing still applies.
        assert client.post("/api/v1/ingest", json=data(),
                           headers={"X-Agent-Token": "c" * 40}).status_code == 429
    # A new process/controlled reload with only the new key invalidates the old.
    setup(monkeypatch, tmp_path, {"node-a": "c" * 40})
    with TestClient(metrics.app) as client:
        assert client.post("/api/v1/ingest", json=data(),
                           headers={"X-Agent-Token": "b" * 40}).status_code == 401
        assert client.post("/api/v1/ingest", json=data(),
                           headers={"X-Agent-Token": "c" * 40}).status_code == 429


def test_cross_node_and_status_token_are_isolated(monkeypatch, tmp_path):
    setup(monkeypatch, tmp_path, {"node-a": ["b" * 40, "c" * 40],
                                  "node-b": "d" * 40})
    monkeypatch.setenv("METRICS_STATUS_TOKEN", "s" * 48)
    with TestClient(metrics.app) as client:
        assert client.post("/api/v1/ingest", json=data(),
                           headers={"X-Agent-Token": "d" * 40}).status_code == 401
        assert client.get("/api/v1/systems",
                          headers={"Authorization": "Bearer " + "c" * 40}).status_code == 401
        assert client.get("/v1/status",
                          headers={"Authorization": "Bearer " + "c" * 40}).status_code == 401


@pytest.mark.parametrize("mapping", [
    {"node-a": []},
    {"node-a": ["b" * 40, "c" * 40, "d" * 40]},
    {"node-a": ["b" * 40, "b" * 40]},
    {"node-a": ["b" * 40], "node-b": "b" * 40},
    {"node-a": ["a" * 40, "b" * 40]},
    {"node-a": {"current": "b" * 40}},
    {"node-a": "bad token with spaces " * 3},
    {"node-a": "b" * 1025},
])
def test_invalid_rotation_configuration_rejected(monkeypatch, tmp_path, mapping):
    setup(monkeypatch, tmp_path, mapping)
    with pytest.raises(RuntimeError):
        with TestClient(metrics.app):
            pass


def test_status_scope_token_must_not_duplicate_rotation_key(monkeypatch, tmp_path):
    setup(monkeypatch, tmp_path, {"node-a": ["b" * 40, "c" * 40]})
    monkeypatch.setenv("METRICS_STATUS_TOKEN", "c" * 40)
    with pytest.raises(RuntimeError, match="METRICS_STATUS_TOKEN"):
        with TestClient(metrics.app):
            pass
