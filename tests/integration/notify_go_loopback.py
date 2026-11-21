#!/usr/bin/env python3
"""Opt-in real Notify contract fixture. No source downloads or persistent services."""
from __future__ import annotations

import argparse
import json
import os
import secrets
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import ProxyHandler, Request, build_opener

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from server.notify_adapter import message_payload  # noqa: E402


def exercise(binary: Path) -> None:
    if not binary.is_file() or binary.is_symlink() or not os.access(binary, os.X_OK):
        raise ValueError("Provide an inspected, executable regular-file Notify binary")
    with tempfile.TemporaryDirectory(prefix="gcm-notify-fixture-") as temp:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        token = secrets.token_urlsafe(48)
        env = dict(os.environ, NOTIFY_API_TOKEN=token,
                   NOTIFY_LISTEN=f"127.0.0.1:{port}",
                   NOTIFY_DATA_FILE=str(Path(temp) / "journal.jsonl"))
        daemon = subprocess.Popen([str(binary)], env=env, cwd=temp,
                                  stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                  stderr=subprocess.DEVNULL)
        opener = build_opener(ProxyHandler({}))
        base = f"http://127.0.0.1:{port}"
        try:
            for _ in range(40):
                try:
                    with opener.open(base + "/healthz", timeout=1) as response:
                        if response.status == 200:
                            break
                except OSError:
                    if daemon.poll() is not None:
                        raise RuntimeError("Notify development service exited")
                    time.sleep(.1)
            else:
                raise RuntimeError("Notify synthetic loopback instance did not become healthy")
            event = {
                "node_id": "synthetic-only",
                "metric": "cpu",
                "state": "firing",
                "message": "Synthetic threshold, no real telemetry",
                "created_ts": 2_000_000_000,
            }
            body = json.dumps(message_payload(event)).encode("utf-8")
            auth = {"Authorization": "Bearer " + token, "Content-Type": "application/json"}
            endpoint = base + "/api/v1/topics/metrics/messages"
            with opener.open(Request(endpoint, data=body, method="POST", headers=auth), timeout=3) as response:
                if response.status not in (200, 201):
                    raise AssertionError("Notify did not accept synthetic alert")
            with opener.open(Request(endpoint + "?limit=20", headers=auth), timeout=3) as response:
                persisted = json.load(response)
            messages = persisted.get("messages", []) if isinstance(persisted, dict) else persisted
            if not any("synthetic-only" in str(message) for message in messages):
                raise AssertionError("Synthetic alert absent from Notify history")
            try:
                opener.open(Request(endpoint + "?limit=20",
                                    headers={"Authorization": "Bearer invalid"}), timeout=3)
            except HTTPError as failure:
                if failure.code != 401:
                    raise AssertionError("Wrong rejection status") from failure
            else:
                raise AssertionError("Notify accepted invalid bearer")
            print("PASS: real development Notify service accepted/persisted synthetic Metrics alert and rejected unauthorized read")
            print("Scope: local-only HTTP fixture, not TLS/Identity/deployed acceptance")
        finally:
            daemon.terminate()
            try:
                daemon.wait(timeout=4)
            except subprocess.TimeoutExpired:
                daemon.kill()
                daemon.wait(timeout=4)


def main() -> int:
    parser = argparse.ArgumentParser(description="Synthetic Metrics / Notify Go loopback contract")
    parser.add_argument("--notify-binary", required=True)
    args = parser.parse_args()
    try:
        exercise(Path(args.notify_binary).expanduser().absolute())
        return 0
    except (OSError, ValueError, RuntimeError, AssertionError) as error:
        print(f"FAIL: Notify contract fixture ({type(error).__name__})", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
