"""Opt-in, bounded local container statistics from Podman or Docker.

WARNING: Docker daemon socket access can convey host-root equivalent powers.
No engine APIs are contacted unless METRICS_CONTAINER_PROVIDER is explicitly set.
"""
from __future__ import annotations

import json
import selectors
import time
import math
import os
import re
import shutil
import subprocess

MAX_BYTES = 200_000
MAX_CONTAINERS = 100
NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,99}$")
MEASURE = re.compile(r"^\s*([0-9]+(?:\.[0-9]+)?)\s*([kKmMgGtTpP]?[iI]?[bB])?\s*$")
SCALE = {"": 1, "b": 1, "kb": 1000, "mb": 1000**2, "gb": 1000**3,
         "tb": 1000**4, "pb": 1000**5, "kib": 1024, "mib": 1024**2,
         "gib": 1024**3, "tib": 1024**4, "pib": 1024**5}


def percentage(value: object) -> float:
    try:
        number = float(str(value).strip().rstrip("%"))
        if not math.isfinite(number):
            return 0.0
        return round(max(0.0, min(number, 100.0)), 2)
    except (ValueError, TypeError):
        return 0.0


def byte_value(value: str) -> int:
    match = MEASURE.fullmatch(value)
    if not match:
        return 0
    amount, unit = match.groups()
    return max(0, int(float(amount) * SCALE.get((unit or "").lower(), 0)))


def network_io(value: object) -> tuple[int, int]:
    if not isinstance(value, str) or "/" not in value:
        return 0, 0
    rx, tx = value.split("/", 1)
    return byte_value(rx), byte_value(tx)


def parse_stats(raw: str) -> list[dict[str, object]]:
    """Accept JSON array (Podman) or one JSON object per line (Docker)."""
    try:
        payload = json.loads(raw)
        values = payload if isinstance(payload, list) else [payload]
    except json.JSONDecodeError:
        values = []
        for line in raw.splitlines():
            try:
                values.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    result = []
    for value in values[:MAX_CONTAINERS]:
        if not isinstance(value, dict):
            continue
        name = str(value.get("Name") or value.get("name") or "").lstrip("/")
        if not NAME.fullmatch(name):
            continue
        network = value.get("NetIO", value.get("netio", ""))
        rx, tx = network_io(network)
        result.append({
            "name": name,
            "cpu_percent": percentage(value.get("CPUPerc", value.get("cpu", "0"))),
            "memory_percent": percentage(value.get("MemPerc", value.get("memperc", "0"))),
            "rx_bytes": rx,
            "tx_bytes": tx,
        })
    return result


def bounded_provider_output(command: list[str]) -> bytes:
    """Linux-only, no shell; enforce output bytes and runtime while reading."""
    started = time.monotonic()
    process = subprocess.Popen(command, stdout=subprocess.PIPE,
                               stderr=subprocess.DEVNULL, shell=False)
    data = bytearray()
    try:
        assert process.stdout is not None
        with selectors.DefaultSelector() as selector:
            selector.register(process.stdout, selectors.EVENT_READ)
            while selector.get_map():
                remaining = 6 - (time.monotonic() - started)
                if remaining <= 0:
                    raise subprocess.TimeoutExpired(command, 6)
                events = selector.select(timeout=remaining)
                if not events:
                    raise subprocess.TimeoutExpired(command, 6)
                for key, _ in events:
                    chunk = os.read(key.fileobj.fileno(),
                                    min(16_384, MAX_BYTES + 1 - len(data)))
                    if not chunk:
                        selector.unregister(key.fileobj)
                        break
                    data.extend(chunk)
                    if len(data) > MAX_BYTES:
                        raise ValueError("Container stats output exceeds safety bound")
        remaining = 6 - (time.monotonic() - started)
        if remaining <= 0:
            raise subprocess.TimeoutExpired(command, 6)
        code = process.wait(timeout=remaining)
        if code != 0:
            raise subprocess.CalledProcessError(code, command)
        return bytes(data)
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=2)
        if process.stdout is not None:
            process.stdout.close()


def collect_containers() -> list[dict[str, object]]:
    provider = os.environ.get("METRICS_CONTAINER_PROVIDER", "").strip().lower()
    if not provider:
        return []
    if provider not in {"podman", "docker"}:
        raise ValueError("METRICS_CONTAINER_PROVIDER must be 'podman' or 'docker'")
    executable = shutil.which(provider)
    if not executable:
        raise OSError("Container provider executable not found")
    command = ([executable, "stats", "--no-stream", "--format", "json"]
               if provider == "podman" else
               [executable, "stats", "--no-stream", "--format", "{{json .}}"])
    raw = bounded_provider_output(command)
    return parse_stats(raw.decode("utf-8", errors="replace"))
