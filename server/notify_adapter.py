"""Optional interoperable adapter for GoreeCloud Notify's verified topic API.

Payload shape is from GoreeCloud/notify/internal/notify/server.go:
POST /api/v1/topics/{topic}/messages {title,body,priority} with bearer auth.
"""
from __future__ import annotations

import os
import re
import urllib.parse


def configured_target() -> tuple[str | None, str | None]:
    base = os.environ.get("METRICS_NOTIFY_BASE_URL", "").strip().rstrip("/")
    token = os.environ.get("METRICS_NOTIFY_API_TOKEN", "").strip()
    topic = os.environ.get("METRICS_NOTIFY_TOPIC", "metrics").strip()
    webhook = os.environ.get("METRICS_WEBHOOK_URL", "").strip()
    if not base and not token:
        return None, None
    if webhook:
        raise ValueError("Configure either GoreeCloud Notify or a generic webhook, not both")
    parsed = urllib.parse.urlsplit(base)
    if (parsed.scheme != "https" or not parsed.hostname or
        parsed.username or parsed.password or parsed.query or parsed.fragment or
        parsed.path not in ("", "/")):
        raise ValueError("GoreeCloud Notify requires an HTTPS origin without path or credentials")
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", topic):
        raise ValueError("Invalid GoreeCloud Notify topic")
    if len(base) > 2048 or not 32 <= len(token) <= 2048:
        raise ValueError("GoreeCloud Notify API token must be configured securely")
    return f"{base}/api/v1/topics/{topic}/messages", token


def message_payload(event: dict) -> dict[str, object]:
    """Translate a transition into a size-bounded GoreeCloud Notify message."""
    state = str(event["state"])
    node = str(event["node_id"])
    metric = str(event["metric"])
    message = str(event["message"])
    title = f"Metrics · {node} · {state}"[:160]
    body = f"{node}: {metric} {state}. {message}"[:4096]
    priority = 5 if metric == "heartbeat" and state == "firing" else (
        4 if state == "firing" else 2
    )
    return {"title": title, "body": body, "priority": priority}
