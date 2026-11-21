"""Source-owned, opt-in and strictly scoped Mesh-facing status contract tests."""
import json
import sqlite3
from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from server import app as metrics


def env(monkeypatch, tmp_path, *, status=None):
    monkeypatch.setenv("METRICS_DB_PATH", str(tmp_path / "metrics.sqlite3"))
    monkeypatch.setenv("METRICS_ADMIN_TOKEN", "a" * 40)
    monkeypatch.setenv("METRICS_AGENT_TOKENS", json.dumps({"node-1": "b" * 40}))
    if status is None:
        monkeypatch.delenv("METRICS_STATUS_TOKEN", raising=False)
    else:
        monkeypatch.setenv("METRICS_STATUS_TOKEN", status)


def test_disabled_status_is_404(monkeypatch, tmp_path):
    env(monkeypatch, tmp_path)
    with TestClient(metrics.app) as client:
        assert client.get("/v1/status").status_code == 404
        assert client.get("/v1/status", headers={"Authorization": "Bearer " + "a" * 40}).status_code == 404


def test_rejects_weak_or_reused_status_token(monkeypatch, tmp_path):
    for token in ("too-short", "a" * 40, "b" * 40, "x" * 1025, "bad token with spaces" * 2):
        env(monkeypatch, tmp_path, status=token)
        with pytest.raises(RuntimeError, match="METRICS_STATUS_TOKEN"):
            with TestClient(metrics.app):
                pass


def test_status_scope_rejects_admin_credentials_and_body(monkeypatch, tmp_path):
    key = "s" * 48
    env(monkeypatch, tmp_path, status=key)
    with TestClient(metrics.app) as client:
        assert client.get("/v1/status").status_code == 401
        assert client.get("/v1/status", headers={"Authorization": "Bearer " + "a" * 40}).status_code == 401
        status_auth = {"Authorization": "Bearer " + key}
        response = client.get("/v1/status", headers=status_auth)
        assert response.status_code == 200
        assert response.headers["cache-control"] == "no-store"
        assert response.headers["x-content-type-options"] == "nosniff"
        assert response.json()["schema_version"] == "metrics.status.v1"
        assert response.json()["state"] == "ok"
        assert set(response.json()) == {"schema_version", "state", "observed_at"}
        stamp = response.json()["observed_at"]
        assert datetime.fromisoformat(stamp.replace("Z", "+00:00")).tzinfo is not None
        assert client.get("/v1/status?extra=1", headers=status_auth).status_code == 400
        assert client.request("GET", "/v1/status", headers=status_auth,
                              content=b"unexpected body").status_code == 400
        assert client.get("/api/v1/systems", headers=status_auth).status_code == 401


def test_degraded_status_is_redacted(monkeypatch, tmp_path):
    key = "s" * 48
    env(monkeypatch, tmp_path, status=key)
    with TestClient(metrics.app) as client:
        monkeypatch.setattr(metrics, "latest_systems",
                            lambda: (_ for _ in ()).throw(sqlite3.OperationalError("private path")))
        response = client.get("/v1/status", headers={"Authorization": "Bearer " + key})
        assert response.status_code == 503
        assert response.json()["state"] == "degraded"
        assert "private path" not in response.text


def test_health_not_green_when_database_is_unavailable(monkeypatch, tmp_path):
    from contextlib import contextmanager
    env(monkeypatch, tmp_path)

    @contextmanager
    def broken_db():
        raise sqlite3.OperationalError("private storage failure")
        yield

    with TestClient(metrics.app) as client:
        assert client.get("/healthz").status_code == 200
        monkeypatch.setattr(metrics, "db", broken_db)
        failed = client.get("/healthz")
        assert failed.status_code == 503
        assert failed.json() == {"status": "unavailable"}
        assert "private storage failure" not in failed.text
