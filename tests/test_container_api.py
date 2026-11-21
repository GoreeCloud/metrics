"""Container API is admin-only and samples are bound to registered hosts."""


from fastapi.testclient import TestClient
from server.app import app


def test_container_ingest_and_access(tmp_path, monkeypatch):
    monkeypatch.setenv("METRICS_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("METRICS_ADMIN_TOKEN", "a" * 40)
    monkeypatch.setenv("METRICS_AGENT_TOKENS", '{"node-1":"' + "b" * 40 + '"}')
    base = {
        "node_id": "node-1", "hostname": "Test",
        "cpu_percent": 4, "memory_percent": 5, "disk_percent": 6,
        "memory_used_bytes": 100, "disk_used_bytes": 100,
        "rx_bytes": 10, "tx_bytes": 20, "uptime_seconds": 500,
        "containers": [{"name": "web-1", "cpu_percent": 20, "memory_percent": 35,
                        "rx_bytes": 1000, "tx_bytes": 2000}]
    }
    url = "/api/v1/systems/node-1/containers"
    admin = {"Authorization": "Bearer " + "a" * 40}
    with TestClient(app) as client:
        assert client.get(url).status_code == 401
        assert client.post("/api/v1/ingest", json=base, headers={"X-Agent-Token": "b" * 40}).status_code == 202
        result = client.get(url, headers=admin).json()
        assert len(result["containers"]) == 1
        assert result["containers"][0]["name"] == "web-1"
        assert client.get("/api/v1/systems/other/containers", headers=admin).status_code == 404


def test_invalid_container_rejected(tmp_path, monkeypatch):
    monkeypatch.setenv("METRICS_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("METRICS_ADMIN_TOKEN", "a" * 40)
    monkeypatch.setenv("METRICS_AGENT_TOKENS", '{"node-1":"' + "b" * 40 + '"}')
    with TestClient(app) as client:
        payload = {
            "node_id": "node-1", "hostname": "Test",
            "cpu_percent": 1, "memory_percent": 1, "disk_percent": 1,
            "memory_used_bytes": 0, "disk_used_bytes": 0,
            "rx_bytes": 0, "tx_bytes": 0, "uptime_seconds": 1,
            "containers": [{"name": "../../etc/shadow", "cpu_percent": 4,
                            "memory_percent": 5, "rx_bytes": 0, "tx_bytes": 0}],
        }
        assert client.post("/api/v1/ingest", json=payload,
                           headers={"X-Agent-Token": "b" * 40}).status_code == 422
