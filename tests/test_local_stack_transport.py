"""End-to-end synthetic loopback proof: actual Uvicorn, agent HTTP and SQLite.

No external network, real host measurements, secrets, persistent services, or
production data. All transport stays bound to 127.0.0.1 and is terminated.
"""
from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import ProxyHandler, Request, build_opener

from agent.agent import report

ROOT = Path(__file__).resolve().parents[1]


def test_isolated_loopback_real_http_ingest_and_readback(monkeypatch, tmp_path):
    token = "b" * 48
    admin = "a" * 48
    status = "s" * 48
    env = dict(os.environ,
               METRICS_DB_PATH=str(tmp_path / "isolated.sqlite3"),
               METRICS_AGENT_TOKENS=json.dumps({"synthetic-node": [token, "c" * 48]}),
               METRICS_ADMIN_TOKEN=admin,
               METRICS_STATUS_TOKEN=status,
               METRICS_RETENTION_DAYS="15",
               NO_PROXY="127.0.0.1,localhost",
               no_proxy="127.0.0.1,localhost")
    for key in (
        "METRICS_WEBHOOK_URL", "METRICS_WEBHOOK_BEARER",
        "METRICS_NOTIFY_URL", "METRICS_NOTIFY_TOKEN",
        "METRICS_CONTAINER_PROVIDER",
    ):
        env.pop(key, None)
    monkeypatch.setenv("no_proxy", "127.0.0.1,localhost")
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    base = f"http://127.0.0.1:{port}"
    opener = build_opener(ProxyHandler({}))
    process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "server.app:app",
         "--host", "127.0.0.1", "--port", str(port),
         "--log-level", "error", "--no-access-log"],
        cwd=ROOT, env=env, stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    try:
        for _ in range(100):
            if process.poll() is not None:
                raise AssertionError("Synthetic Uvicorn child exited before health")
            try:
                with opener.open(base + "/healthz", timeout=0.5) as response:
                    if response.status == 200:
                        break
            except OSError:
                time.sleep(0.05)
        else:
            raise AssertionError("Synthetic loopback hub did not become ready")
        with opener.open(Request(
            base + "/v1/status",
            headers={"Authorization": "Bearer " + status}
        ), timeout=2) as response:
            status_payload = json.load(response)
        assert status_payload["schema_version"] == "metrics.status.v1"
        assert status_payload["state"] == "ok"
        sample = {
            "node_id": "synthetic-node", "hostname": "Synthetic isolated host",
            "cpu_percent": 96, "memory_percent": 45, "disk_percent": 22,
            "memory_used_bytes": 1000, "disk_used_bytes": 5000,
            "rx_bytes": 500, "tx_bytes": 300, "uptime_seconds": 120,
            "containers": [{"name": "synthetic-container", "cpu_percent": 8,
                            "memory_percent": 10, "rx_bytes": 123, "tx_bytes": 456}],
        }
        report(base, token, sample)
        headers = {"Authorization": "Bearer " + admin}
        with opener.open(Request(base + "/api/v1/config", headers=headers),
                         timeout=2) as response:
            assert json.load(response)["retention_days"] == 15
        with opener.open(Request(base + "/api/v1/systems", headers=headers),
                         timeout=2) as response:
            hosts = json.load(response)["systems"]
        assert len(hosts) == 1 and hosts[0]["node_id"] == "synthetic-node"
        assert hosts[0]["cpu"] == 96
        with opener.open(Request(base + "/api/v1/systems/synthetic-node/history",
                                 headers=headers), timeout=2) as response:
            assert len(json.load(response)["samples"]) == 1
        with opener.open(Request(base + "/api/v1/systems/synthetic-node/containers",
                                 headers=headers), timeout=2) as response:
            assert json.load(response)["containers"][0]["name"] == "synthetic-container"
        with opener.open(Request(base + "/api/v1/alerts", headers=headers),
                         timeout=2) as response:
            assert any(a["metric"] == "cpu" for a in json.load(response)["alerts"])
        with opener.open(Request(base + "/api/v1/metrics", headers=headers),
                         timeout=2) as response:
            assert b"goreecloud_host_cpu_percent" in response.read(20_000)
        try:
            opener.open(Request(base + "/api/v1/systems",
                                headers={"Authorization": "Bearer " + status}),
                        timeout=2)
        except HTTPError as error:
            assert error.code == 401
        else:
            raise AssertionError("Status scope unexpectedly read private host data")
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
    assert process.poll() is not None
