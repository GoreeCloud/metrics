"""Low-privilege host statistics reporter for GoreeCloud Metrics."""
from __future__ import annotations

import argparse
import json
import os
import re
import signal
import subprocess
import socket
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

import psutil
from agent.container_stats import collect_containers

_STOP = False


def stop(_signum, _frame):
    global _STOP
    _STOP = True


def settings():
    hub = os.environ.get("METRICS_HUB_URL", "").rstrip("/")
    token = os.environ.get("METRICS_AGENT_TOKEN", "")
    node_id = os.environ.get("METRICS_NODE_ID", "")
    parsed = urllib.parse.urlsplit(hub)
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,62}", node_id):
        raise ValueError("METRICS_NODE_ID must be a lowercase alphanumeric/hyphen ID")
    if len(token) < 32:
        raise ValueError("METRICS_AGENT_TOKEN must have at least 32 characters")
    if parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path not in ("", "/"):
        raise ValueError("METRICS_HUB_URL must be a clean base URL without credentials")
    if parsed.scheme != "https" and not (
        parsed.scheme == "http" and parsed.hostname in ("localhost", "127.0.0.1", "::1")
    ):
        raise ValueError("HTTPS required outside loopback")
    if not parsed.hostname:
        raise ValueError("METRICS_HUB_URL must be set")
    return hub, node_id, token


def collect(node_id: str):
    disk = psutil.disk_usage(os.environ.get("METRICS_DISK_PATH", "/"))
    network = psutil.net_io_counters()
    memory = psutil.virtual_memory()
    result = {
        "node_id": node_id,
        "hostname": socket.gethostname()[:128],
        "cpu_percent": psutil.cpu_percent(interval=0.5),
        "memory_percent": memory.percent,
        "disk_percent": disk.percent,
        "memory_used_bytes": memory.used,
        "disk_used_bytes": disk.used,
        "rx_bytes": network.bytes_recv,
        "tx_bytes": network.bytes_sent,
        "uptime_seconds": max(0, time.time() - psutil.boot_time()),
    }
    try:
        result["containers"] = collect_containers()
    except (OSError, ValueError, TimeoutError, subprocess.SubprocessError) as exc:
        # Container collection is opt-in and must never block host telemetry.
        print(f"Container stats unavailable ({type(exc).__name__})", file=sys.stderr)
    return result


def report(hub: str, token: str, sample: dict):
    body = json.dumps(sample, separators=(",", ":")).encode("utf-8")
    request = urllib.request.Request(
        f"{hub}/api/v1/ingest", data=body,
        headers={"Content-Type": "application/json", "X-Agent-Token": token},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        if response.status != 202:
            raise RuntimeError("Unexpected ingest status")


def main():
    parser = argparse.ArgumentParser(description="GoreeCloud Metrics host agent")
    parser.add_argument("--once", action="store_true", help="Send one sample, then exit")
    args = parser.parse_args()
    try:
        hub, node_id, token = settings()
    except ValueError as exc:
        parser.error(str(exc))
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    while not _STOP:
        try:
            report(hub, token, collect(node_id))
        except (OSError, RuntimeError, urllib.error.URLError) as exc:
            # Deliberately omit request URL, credentials and exception body.
            print(f"Metric send failed ({type(exc).__name__})", file=sys.stderr)
        if args.once:
            break
        for _ in range(30):
            if _STOP:
                break
            time.sleep(1)


if __name__ == "__main__":
    main()
