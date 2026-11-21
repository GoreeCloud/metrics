"""Optional durable alert-transition journal and HTTPS webhook delivery.

Run explicitly as an operator-managed service. This is NOT started by API
startup, does not send data without the operator's webhook opt-in, and cannot
execute host commands. Delivery is at least once (duplicates possible).
"""
from __future__ import annotations

import argparse
import json
import os
import signal
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

from server.alert_rules import AlertRules, evaluate
from server.app import db, init_db, latest_systems
from server.notify_adapter import configured_target, message_payload

_STOP = False


def webhook_configuration() -> tuple[str | None, str | None]:
    url = os.environ.get("METRICS_WEBHOOK_URL", "").strip()
    token = os.environ.get("METRICS_WEBHOOK_BEARER", "").strip()
    if not url:
        return None, None
    parsed = urllib.parse.urlsplit(url)
    if (parsed.scheme != "https" or not parsed.hostname or parsed.username or
        parsed.password or parsed.fragment or parsed.query):
        raise ValueError("Webhook must be an HTTPS URL without credentials, query or fragment")
    if len(url) > 2048 or len(token) > 2048:
        raise ValueError("Webhook configuration too long")
    return url, token or None


def initialize_journal() -> None:
    with db() as connection:
        connection.executescript("""
            CREATE TABLE IF NOT EXISTS alert_state (
                node_id TEXT NOT NULL,
                metric TEXT NOT NULL,
                message TEXT NOT NULL,
                PRIMARY KEY (node_id, metric)
            );
            CREATE TABLE IF NOT EXISTS alert_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                node_id TEXT NOT NULL, metric TEXT NOT NULL,
                state TEXT NOT NULL, message TEXT NOT NULL,
                created_ts INTEGER NOT NULL, sent_ts INTEGER,
                attempts INTEGER NOT NULL DEFAULT 0,
                next_attempt_ts INTEGER NOT NULL DEFAULT 0
            );
            CREATE INDEX IF NOT EXISTS alert_events_time
                ON alert_events(created_ts DESC);
        """)


def record_transitions(active: list[dict[str, str]], *, now: int | None = None) -> int:
    current = {(item["node_id"], item["metric"]): item["message"] for item in active}
    stamp = int(time.time()) if now is None else now
    emitted = 0
    with db() as connection:
        connection.execute("BEGIN IMMEDIATE")
        prior = {(r["node_id"], r["metric"]): r["message"] for r in
                 connection.execute("SELECT node_id,metric,message FROM alert_state")}
        for key, message in current.items():
            if key not in prior:
                connection.execute("INSERT INTO alert_events (node_id,metric,state,message,created_ts) VALUES (?,?,?,?,?)",
                                   (*key, "firing", message, stamp))
                emitted += 1
            connection.execute(
                """INSERT INTO alert_state(node_id,metric,message) VALUES (?,?,?)
                ON CONFLICT(node_id,metric) DO UPDATE SET message=excluded.message""",
                (*key, message))
        for key, old_message in prior.items():
            if key not in current:
                connection.execute("DELETE FROM alert_state WHERE node_id=? AND metric=?", key)
                connection.execute("INSERT INTO alert_events (node_id,metric,state,message,created_ts) VALUES (?,?,?,?,?)",
                                   (*key, "resolved", old_message, stamp))
                emitted += 1
        connection.execute("DELETE FROM alert_events WHERE created_ts < ?", (stamp - 30*86400,))
    return emitted


class RejectRedirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError("Webhook redirects are not permitted")


def deliver_pending(url: str | None, token: str | None, *, now: int | None = None,
                    notify_mode: bool = False) -> tuple[int, int]:
    if not url:
        return 0, 0
    stamp = int(time.time()) if now is None else now
    delivered = failed = 0
    with db() as connection:
        # Atomic event claims are committed before network IO. A second worker
        # cannot select the same event during the 60s claim lease. A crashed
        # worker leaves the claim to expire so an eligible event can retry.
        connection.execute("BEGIN IMMEDIATE")
        entries = connection.execute(
            """SELECT id,node_id,metric,state,message,created_ts,attempts
            FROM alert_events
            WHERE sent_ts IS NULL AND attempts < 5 AND next_attempt_ts <= ?
            ORDER BY id LIMIT 25""", (stamp,)
        ).fetchall()
        for event in entries:
            connection.execute(
                """UPDATE alert_events
                   SET attempts=attempts+1, next_attempt_ts=?
                   WHERE id=? AND sent_ts IS NULL""",
                (stamp + 60, event["id"])
            )
    opener = urllib.request.build_opener(RejectRedirects())
    for event in entries:
        original = {key: event[key] for key in ("node_id", "metric", "state", "message", "created_ts")}
        payload = message_payload(original) if notify_mode else original
        headers = {"Content-Type": "application/json", "User-Agent": "GoreeCloud-Metrics-Notifier/0.1"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        request = urllib.request.Request(
            url, data=json.dumps(payload, separators=(",", ":")).encode("utf-8"),
            headers=headers, method="POST"
        )
        try:
            with opener.open(request, timeout=8) as response:
                if not 200 <= response.status < 300:
                    raise OSError("Non-2xx response")
        except (OSError, ValueError, urllib.error.URLError):
            failed += 1
            with db() as connection:
                delay = min(3600, 30 * 2 ** min(int(event["attempts"]), 6))
                connection.execute(
                    """UPDATE alert_events SET
                    next_attempt_ts=? WHERE id=? AND sent_ts IS NULL""",
                    (stamp + delay, event["id"])
                )
        else:
            delivered += 1
            with db() as connection:
                connection.execute(
                    "UPDATE alert_events SET sent_ts=? WHERE id=? AND sent_ts IS NULL",
                    (stamp, event["id"])
                )
    return delivered, failed


def run_once() -> tuple[int, int, int]:
    rules = AlertRules.from_environment()
    notify_url, notify_token = configured_target()
    url, token = (notify_url, notify_token) if notify_url else webhook_configuration()
    init_db()
    initialize_journal()
    systems = latest_systems()
    # Real-time heartbeat is determined by the hub; no synthetic telemetry.
    active = evaluate(systems, rules)
    transitions = record_transitions(active)
    delivered, failed = deliver_pending(url, token, notify_mode=bool(notify_url))
    return transitions, delivered, failed


def shutdown(_signum, _frame):
    global _STOP
    _STOP = True


def main() -> int:
    parser = argparse.ArgumentParser(description="Opt-in Metrics transition journal + notifier")
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)
    while not _STOP:
        try:
            events, delivered, failed = run_once()
            print(f"alert transitions={events}, delivered={delivered}, failed={failed}")
        except (OSError, ValueError) as exc:
            print(f"Alert worker failed ({type(exc).__name__})", file=sys.stderr)
            if args.once:
                return 2
        if args.once:
            break
        for _ in range(30):
            if _STOP:
                break
            time.sleep(1)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
