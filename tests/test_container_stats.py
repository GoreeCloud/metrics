"""Tests never execute a real local container daemon."""
import json
import subprocess

import pytest
from agent import container_stats


def test_parser_and_units():
    assert container_stats.percentage("250%") == 100.0
    assert container_stats.percentage("-5%") == 0.0
    raw = json.dumps([
        {"Name": "web-1", "CPUPerc": "8.41%", "MemPerc": "12.1%",
         "NetIO": "1.2MiB / 30kB"},
        {"Name": "../unsafe", "CPUPerc": "1%", "MemPerc": "2%"},
    ])
    result = container_stats.parse_stats(raw)
    assert result == [{"name": "web-1", "cpu_percent": 8.41, "memory_percent": 12.1,
                       "rx_bytes": 1258291, "tx_bytes": 30000}]
    assert container_stats.parse_stats('{"Name":"api","CPUPerc":"25%"}\n{"Name":"db"}')[-1]["name"] == "db"


def test_disabled_never_executes(monkeypatch):
    monkeypatch.delenv("METRICS_CONTAINER_PROVIDER", raising=False)
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: pytest.fail("Must be inert"))
    assert container_stats.collect_containers() == []


def test_podman_uses_bounded_non_shell_command(monkeypatch):
    monkeypatch.setenv("METRICS_CONTAINER_PROVIDER", "podman")
    monkeypatch.setattr(container_stats.shutil, "which", lambda _: "/usr/bin/podman")
    requests = []

    def fake_run(command, **kwargs):
        requests.append((command, kwargs))
        return subprocess.CompletedProcess(command, 0, b'[{"Name":"demo","CPUPerc":"9%"}]', b"")

    monkeypatch.setattr(subprocess, "run", fake_run)
    result = container_stats.collect_containers()
    assert result[0]["name"] == "demo"
    assert requests[0][0] == ["/usr/bin/podman", "stats", "--no-stream", "--format", "json"]
    assert requests[0][1]["timeout"] == 6
    assert "shell" not in requests[0][1]


def test_invalid_provider_rejected(monkeypatch):
    monkeypatch.setenv("METRICS_CONTAINER_PROVIDER", "bash")
    with pytest.raises(ValueError):
        container_stats.collect_containers()


def test_excessive_stats_output_is_rejected(monkeypatch):
    monkeypatch.setenv("METRICS_CONTAINER_PROVIDER", "podman")
    monkeypatch.setattr(container_stats.shutil, "which", lambda _: "/usr/bin/podman")
    monkeypatch.setattr(subprocess, "run", lambda *a, **k:
                        subprocess.CompletedProcess(a[0], 0, b"x" * (container_stats.MAX_BYTES + 1), b""))
    with pytest.raises(ValueError, match="safety bound"):
        container_stats.collect_containers()


def test_container_failure_does_not_block_host_telemetry(monkeypatch):
    from agent import agent
    monkeypatch.setattr(agent, "collect_containers",
                        lambda: (_ for _ in ()).throw(OSError("synthetic provider unavailable")))
    sample = agent.collect("test-host")
    assert sample["node_id"] == "test-host"
    assert "cpu_percent" in sample
    assert "containers" not in sample
