"""Explicit HTTPS/loopback CORS policy, no wildcard or origin redirects."""
from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from fastapi.middleware.cors import CORSMiddleware
from server.app import configured_allowed_origins


def test_none_and_exact_deduplicated_origins(monkeypatch):
    monkeypatch.delenv("METRICS_ALLOWED_ORIGINS", raising=False)
    assert configured_allowed_origins() == []
    monkeypatch.setenv("METRICS_ALLOWED_ORIGINS",
                       "https://owner.example.test, https://owner.example.test, "
                       "http://localhost:5173,http://[::1]:5173")
    assert configured_allowed_origins() == [
        "https://owner.example.test", "http://localhost:5173",
        "http://[::1]:5173",
    ]


@pytest.mark.parametrize("raw", [
    "*", "https://*", "http://owner.example.test", "http://0.0.0.0:8093",
    "https://owner.example.test/", "https://owner.example.test/path",
    "https://owner.example.test?token=secret",
    "https://owner.example.test#anchor", "https://name:pass@owner.example.test",
    "https://bad_host.example.test", "https://owner.example.test:99999",
    "https://owner.example.test:bad", "https://owner.example.test:0",
    "https://owner.example.test,", ",https://owner.example.test",
    "https://owner.example.test, ", "file:///etc/passwd", "null",
    "https://a b.example.test", "http://[fe80::1]:5173",
])
def test_unsafe_origins_fail_startup_validation(monkeypatch, raw):
    monkeypatch.setenv("METRICS_ALLOWED_ORIGINS", raw)
    with pytest.raises(ValueError, match="METRICS_ALLOWED_ORIGINS"):
        configured_allowed_origins()


def test_limit_explicit_allowed_origins(monkeypatch):
    monkeypatch.setenv("METRICS_ALLOWED_ORIGINS",
                       ",".join(f"https://a{i}.example.test" for i in range(33)))
    with pytest.raises(ValueError, match="at most 32"):
        configured_allowed_origins()


def test_cors_headers_only_for_explicit_trusted_origin(monkeypatch):
    monkeypatch.setenv("METRICS_ALLOWED_ORIGINS", "https://owner.example.test")
    test_app = FastAPI()
    test_app.add_middleware(
        CORSMiddleware,
        allow_origins=configured_allowed_origins(),
        allow_methods=["GET"],
        allow_headers=["Authorization"],
    )

    @test_app.get("/probe")
    def probe():
        return {"ok": True}

    with TestClient(test_app) as client:
        trusted = client.get("/probe", headers={"Origin": "https://owner.example.test"})
        assert trusted.status_code == 200
        assert trusted.headers["access-control-allow-origin"] == "https://owner.example.test"
        unknown = client.get("/probe", headers={"Origin": "https://unknown.example.test"})
        assert unknown.status_code == 200
        assert "access-control-allow-origin" not in unknown.headers
        bad_preflight = client.options(
            "/probe",
            headers={"Origin": "https://unknown.example.test",
                     "Access-Control-Request-Method": "GET",
                     "Access-Control-Request-Headers": "Authorization"},
        )
        assert bad_preflight.status_code == 400
