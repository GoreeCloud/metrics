import os
import pytest
from agent.agent import settings


def test_remote_http_refused(monkeypatch):
    monkeypatch.setenv("METRICS_NODE_ID", "host-a")
    monkeypatch.setenv("METRICS_AGENT_TOKEN", "x" * 40)
    monkeypatch.setenv("METRICS_HUB_URL", "http://metrics.example.net")
    with pytest.raises(ValueError, match="HTTPS"):
        settings()


def test_loopback_allowed(monkeypatch):
    monkeypatch.setenv("METRICS_NODE_ID", "host-a")
    monkeypatch.setenv("METRICS_AGENT_TOKEN", "x" * 40)
    monkeypatch.setenv("METRICS_HUB_URL", "http://127.0.0.1:8093")
    assert settings()[1] == "host-a"
