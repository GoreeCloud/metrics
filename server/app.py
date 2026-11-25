"""GoreeCloud Metrics: authenticated, self-hosted metrics hub."""
from __future__ import annotations

import csv
import hmac
import io
import math
import json
import os
import re
import sqlite3
from urllib.parse import urlsplit
from datetime import datetime, timezone
import time
from contextlib import asynccontextmanager, contextmanager
from pathlib import Path
from typing import Annotated, Iterator

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel, Field
from server.alert_rules import AlertRules, evaluate

IDENTIFIER = r"^[a-z0-9][a-z0-9-]{0,62}$"
RETENTION_DAYS = 30
SCHEMA_VERSION = 1
# Version 1 records the historical host/container tables and indexes.
# No destructive or automatic migration is performed for unknown versions.


def retention_days() -> int:
    try:
        days = int(os.environ.get("METRICS_RETENTION_DAYS", str(RETENTION_DAYS)))
    except ValueError as exc:
        raise ValueError("METRICS_RETENTION_DAYS must be an integer") from exc
    if not 1 <= days <= 365:
        raise ValueError("METRICS_RETENTION_DAYS must be 1 through 365")
    return days
ONLINE_SECONDS = 120


class ContainerSample(BaseModel):
    name: str = Field(min_length=1, max_length=100,
                      pattern=r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,99}$")
    cpu_percent: float = Field(ge=0, le=100)
    memory_percent: float = Field(ge=0, le=100)
    rx_bytes: int = Field(ge=0)
    tx_bytes: int = Field(ge=0)


class Sample(BaseModel):
    node_id: str = Field(min_length=1, max_length=63, pattern=IDENTIFIER)
    hostname: str = Field(min_length=1, max_length=128)
    cpu_percent: float = Field(ge=0, le=100)
    memory_percent: float = Field(ge=0, le=100)
    disk_percent: float = Field(ge=0, le=100)
    memory_used_bytes: int = Field(ge=0)
    disk_used_bytes: int = Field(ge=0)
    rx_bytes: int = Field(ge=0)
    tx_bytes: int = Field(ge=0)
    uptime_seconds: float = Field(ge=0)
    containers: list[ContainerSample] = Field(default_factory=list, max_length=100)


def config() -> tuple[str, dict[str, tuple[str, ...]]]:
    admin = os.environ.get("METRICS_ADMIN_TOKEN", "")
    if len(admin) < 32:
        raise RuntimeError("METRICS_ADMIN_TOKEN must be at least 32 characters")
    try:
        agents = json.loads(os.environ.get("METRICS_AGENT_TOKENS", "{}"))
    except json.JSONDecodeError as error:
        raise RuntimeError("METRICS_AGENT_TOKENS must be a JSON object") from error
    if not isinstance(agents, dict) or not agents:
        raise RuntimeError("Configure at least one agent in METRICS_AGENT_TOKENS")
    # One active token, or a two-token rotation window (old, new). No
    # credential can be valid for two hosts or any other API privilege.
    normalized: dict[str, tuple[str, ...]] = {}
    seen = set()
    for node, configured in agents.items():
        if not isinstance(node, str) or not re.fullmatch(IDENTIFIER, node):
            raise RuntimeError("METRICS_AGENT_TOKENS contains an invalid node identifier")
        tokens = (configured,) if isinstance(configured, str) else configured
        if not isinstance(tokens, (list, tuple)) or not 1 <= len(tokens) <= 2:
            raise RuntimeError("METRICS_AGENT_TOKENS accepts one or two tokens per node")
        for token in tokens:
            if (not isinstance(token, str) or not 32 <= len(token) <= 1024
                    or not re.fullmatch(r"[A-Za-z0-9._~+/-]{32,1024}={0,2}", token)
                    or hmac.compare_digest(admin, token) or token in seen):
                raise RuntimeError("Agent tokens must be unique, strong and safe")
            seen.add(token)
        normalized[node] = tuple(tokens)
    return admin, normalized


def configured_status_token(admin: str, agents: dict[str, tuple[str, ...]]) -> str | None:
    """Third opt-in bearer credential for a narrow, redacted integration status."""
    token = os.environ.get("METRICS_STATUS_TOKEN", "")
    if not token:
        return None
    if (not 32 <= len(token) <= 1024
            or not re.fullmatch(r"[A-Za-z0-9._~+/-]{32,1024}={0,2}", token)
            or hmac.compare_digest(token, admin)
            or any(hmac.compare_digest(token, candidate)
                   for tokens in agents.values() for candidate in tokens)):
        raise RuntimeError("METRICS_STATUS_TOKEN must be distinct and 32-1024 safe characters")
    return token


@contextmanager
def db() -> Iterator[sqlite3.Connection]:
    path = Path(os.environ.get("METRICS_DB_PATH", "./data/metrics.sqlite3"))
    # Match the storage CLI's no-symlink boundary. An operator-configured
    # path must not redirect the hub's privileged SQLite writes to another file.
    if path.is_symlink():
        raise OSError("Metrics database file must not be a symlink")
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fresh = not path.exists()
    connection = sqlite3.connect(path, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys=ON")
    connection.execute("PRAGMA busy_timeout=10000")
    try:
        if fresh:
            os.chmod(path, 0o600)
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def init_db() -> None:
    with db() as connection:
        # Inspect version/identity without first mutating SQLite journal mode.
        version = connection.execute("PRAGMA user_version").fetchone()[0]
        if version > SCHEMA_VERSION or version < 0:
            raise RuntimeError("Metrics SQLite schema is newer or unsupported; refuse to modify")
        existing = {row[0] for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )}
        expected = {
            "systems": {"node_id", "hostname", "first_seen", "last_seen"},
            "samples": {"id", "node_id", "ts", "cpu", "memory", "disk",
                        "memory_bytes", "disk_bytes", "rx_bytes",
                        "tx_bytes", "uptime_seconds"},
            "container_samples": {"id", "node_id", "ts", "name", "cpu",
                                  "memory", "rx_bytes", "tx_bytes"},
        }
        # A partial core schema is never silently replaced; the operator
        # must restore a known-good backup or perform a reviewed migration.
        if bool("systems" in existing) != bool("samples" in existing):
            raise RuntimeError("Incomplete Metrics core schema; manual recovery required")
        core = {"systems", "samples"}
        if "container_samples" in existing and not core.issubset(existing):
            raise RuntimeError("Incomplete Metrics container schema; manual recovery required")
        # Never silently co-opt an unrelated database, nor recreate missing
        # core tables in a database already marked as Metrics schema v1.
        user_tables = existing - {"sqlite_sequence"}
        if not core.issubset(existing) and user_tables:
            raise RuntimeError("Unrecognized existing database; refuse to modify")
        if version == SCHEMA_VERSION and not set(expected).issubset(existing):
            raise RuntimeError("Incomplete versioned Metrics schema; manual recovery required")
        for table, required_columns in expected.items():
            if table in existing:
                actual = {row[1] for row in connection.execute(
                    f"PRAGMA table_info({table})"
                )}
                if not required_columns.issubset(actual):
                    raise RuntimeError("Unsupported Metrics SQLite table layout")
        connection.execute("PRAGMA journal_mode=WAL")
        connection.executescript("""
            CREATE TABLE IF NOT EXISTS systems (
                node_id TEXT PRIMARY KEY,
                hostname TEXT NOT NULL,
                first_seen INTEGER NOT NULL,
                last_seen INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS samples (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                node_id TEXT NOT NULL REFERENCES systems(node_id) ON DELETE CASCADE,
                ts INTEGER NOT NULL,
                cpu REAL NOT NULL, memory REAL NOT NULL, disk REAL NOT NULL,
                memory_bytes INTEGER NOT NULL, disk_bytes INTEGER NOT NULL,
                rx_bytes INTEGER NOT NULL, tx_bytes INTEGER NOT NULL,
                uptime_seconds REAL NOT NULL
            );
            CREATE INDEX IF NOT EXISTS samples_node_time
                ON samples(node_id, ts DESC);
            -- Latest host sample, counter rates and cursor-paginated exports
            -- order by the monotonic id rather than by the timestamp.
            CREATE INDEX IF NOT EXISTS samples_node_id_desc
                ON samples(node_id, id DESC);
            CREATE INDEX IF NOT EXISTS samples_time ON samples(ts);
            CREATE TABLE IF NOT EXISTS container_samples (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                node_id TEXT NOT NULL REFERENCES systems(node_id) ON DELETE CASCADE,
                ts INTEGER NOT NULL,
                name TEXT NOT NULL,
                cpu REAL NOT NULL, memory REAL NOT NULL,
                rx_bytes INTEGER NOT NULL, tx_bytes INTEGER NOT NULL
            );
            CREATE INDEX IF NOT EXISTS container_samples_node_time
                ON container_samples(node_id, ts DESC);
        """)
        # SQLite PRAGMA user_version is owner-local schema metadata. Old
        # unversioned databases with the verified core table layout are
        # upgraded in place without dropping any samples.
        if version == 0:
            connection.execute(f"PRAGMA user_version={SCHEMA_VERSION}")


@asynccontextmanager
async def lifespan(application: FastAPI):
    admin, agents = config()
    application.state.alert_rules = AlertRules.from_environment()
    application.state.retention_days = retention_days()
    application.state.status_token = configured_status_token(admin, agents)
    application.state.admin = admin
    application.state.agents = agents
    init_db()
    yield


app = FastAPI(
    title="GoreeCloud Metrics API", version="0.1.0",
    docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan
)
def configured_allowed_origins() -> list[str]:
    """Fail closed on wildcard, cleartext remote or malformed owner origins."""
    raw = os.environ.get("METRICS_ALLOWED_ORIGINS", "")
    if not raw.strip():
        return []
    origins: list[str] = []
    for value in raw.split(","):
        origin = value.strip()
        if not origin or len(origin) > 512 or any(char.isspace() for char in origin):
            raise ValueError("METRICS_ALLOWED_ORIGINS contains an invalid origin")
        try:
            parsed = urlsplit(origin)
            port = parsed.port
        except ValueError as exc:
            raise ValueError("METRICS_ALLOWED_ORIGINS has an invalid host or port") from exc
        is_loopback = parsed.hostname in ("localhost", "127.0.0.1", "::1")
        if (parsed.scheme not in ("https", "http")
                or (parsed.scheme == "http" and not is_loopback)
                or not parsed.netloc or not parsed.hostname
                or parsed.username is not None or parsed.password is not None
                or parsed.path or parsed.query or parsed.fragment
                or not (re.fullmatch(r"[A-Za-z0-9.-]{1,253}", parsed.hostname)
                        or (parsed.hostname == "::1" and parsed.netloc.startswith("[")))
                or (port is not None and not 1 <= port <= 65535)):
            raise ValueError("METRICS_ALLOWED_ORIGINS requires an exact HTTPS origin or loopback HTTP")
        if origin not in origins:
            origins.append(origin)
    if len(origins) > 32:
        raise ValueError("METRICS_ALLOWED_ORIGINS supports at most 32 explicit origins")
    return origins


origins = configured_allowed_origins()
if origins:
    app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=["GET"],
                       allow_headers=["Authorization"])


# ASGI ingestion bodies are bounded *before* FastAPI/Pydantic JSON parsing.
MAX_INGEST_BYTES = 64 * 1024


@app.middleware("http")
async def ingest_admission(request: Request, call_next):
    if request.method != "POST" or request.url.path != "/api/v1/ingest":
        return await call_next(request)
    # A token cannot authorize an arbitrary node_id. This is a cheap first
    # gate only; check_agent still enforces the node-specific credential.
    provided = request.headers.getlist("x-agent-token")
    supplied = provided[0] if len(provided) == 1 else ""
    authorized = False
    for configured in request.app.state.agents.values():
        active = (configured,) if isinstance(configured, str) else configured
        for candidate in active:
            authorized |= hmac.compare_digest(supplied, candidate)
    if not authorized:
        return JSONResponse(status_code=401, content={"detail": "Unauthorized"})
    media = request.headers.get("content-type", "").split(";", 1)[0].strip().lower()
    if media != "application/json":
        return JSONResponse(status_code=415, content={"detail": "application/json required"})
    values = request.headers.getlist("content-length")
    if len(values) > 1 or (values and (not values[0].isdigit())):
        return JSONResponse(status_code=400, content={"detail": "Invalid request size"})
    if values and int(values[0]) > MAX_INGEST_BYTES:
        return JSONResponse(status_code=413, content={"detail": "Ingest request too large"})
    content = bytearray()
    async for chunk in request.stream():
        if len(content) + len(chunk) > MAX_INGEST_BYTES:
            return JSONResponse(status_code=413, content={"detail": "Ingest request too large"})
        content.extend(chunk)
    # Starlette's cached request body is replayed to FastAPI's normal parser.
    request._body = bytes(content)
    return await call_next(request)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Cache-Control"] = "no-store"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response


def require_admin(request: Request, authorization: Annotated[str | None, Header()] = None) -> None:
    scheme, _, token = (authorization or "").partition(" ")
    if scheme.lower() != "bearer" or not hmac.compare_digest(token, request.app.state.admin):
        raise HTTPException(401, "Unauthorized", headers={"WWW-Authenticate": "Bearer"})


def check_agent(request: Request, sample: Sample, key: str | None) -> None:
    candidates = request.app.state.agents.get(sample.node_id, ())
    # A valid credential for another system never authorizes this node.
    valid = False
    for expected in candidates:
        valid |= hmac.compare_digest(key or "", expected)
    if not valid:
        raise HTTPException(401, "Unauthorized")


@app.get("/v1/status")
def scoped_status(request: Request, authorization: Annotated[str | None, Header()] = None):
    """Dedicated status-only scope; no agent or administrator data is returned."""
    expected = request.app.state.status_token
    if expected is None:
        raise HTTPException(404, "Not Found")
    scheme, _, token = (authorization or "").partition(" ")
    if scheme.lower() != "bearer" or not hmac.compare_digest(token, expected):
        raise HTTPException(401, "Unauthorized", headers={"WWW-Authenticate": "Bearer"})
    content_length = request.headers.get("content-length", "0")
    if (request.url.query or not content_length.isdecimal() or int(content_length) != 0
            or "transfer-encoding" in request.headers):
        raise HTTPException(400, "Status requests must not include query parameters or a body")
    status_code, state = 200, "ok"
    try:
        latest_systems()  # Readback only; no host information leaves the owner.
    except (sqlite3.DatabaseError, OSError):
        status_code, state = 503, "degraded"
    timestamp = datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
    return JSONResponse(status_code=status_code, content={
        "schema_version": "metrics.status.v1", "state": state, "observed_at": timestamp,
    })


@app.get("/healthz")
def health():
    """Public liveness/readiness probe with bounded, redacted DB status."""
    try:
        with db() as connection:
            connection.execute("SELECT 1 FROM systems LIMIT 1").fetchone()
    except (sqlite3.DatabaseError, OSError):
        return JSONResponse(status_code=503, content={"status": "unavailable"})
    return {"status": "ok"}


@app.post("/api/v1/ingest", status_code=202)
def ingest(sample: Sample, request: Request, x_agent_token: Annotated[str | None, Header()] = None):
    check_agent(request, sample, x_agent_token)
    now = int(time.time())
    with db() as connection:
        connection.execute("BEGIN IMMEDIATE")
        prior = connection.execute(
            "SELECT last_seen FROM systems WHERE node_id = ?", (sample.node_id,)
        ).fetchone()
        if prior and now - prior["last_seen"] < 5:
            raise HTTPException(429, "Samples must be spaced by at least 5 seconds")
        connection.execute(
            """INSERT INTO systems (node_id, hostname, first_seen, last_seen)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(node_id) DO UPDATE SET
               hostname=excluded.hostname,last_seen=excluded.last_seen""",
            (sample.node_id, sample.hostname, now, now)
        )
        connection.execute(
            """INSERT INTO samples
               (node_id,ts,cpu,memory,disk,memory_bytes,disk_bytes,
                rx_bytes,tx_bytes,uptime_seconds)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (sample.node_id, now, sample.cpu_percent, sample.memory_percent,
             sample.disk_percent, sample.memory_used_bytes, sample.disk_used_bytes,
             sample.rx_bytes, sample.tx_bytes, sample.uptime_seconds)
        )
        for item in sample.containers:
            connection.execute(
                """INSERT INTO container_samples
                (node_id,ts,name,cpu,memory,rx_bytes,tx_bytes)
                VALUES (?,?,?,?,?,?,?)""",
                (sample.node_id, now, item.name, item.cpu_percent,
                 item.memory_percent, item.rx_bytes, item.tx_bytes)
            )
        cutoff = now - request.app.state.retention_days * 86400
        connection.execute("DELETE FROM container_samples WHERE ts < ?", (cutoff,))
        connection.execute("DELETE FROM samples WHERE ts < ?", (cutoff,))
    return {"accepted": True, "server_ts": now}


def latest_systems() -> list[dict]:
    with db() as connection:
        rows = connection.execute("""
            SELECT s.node_id, s.hostname, s.first_seen, s.last_seen,
                m.ts, m.cpu, m.memory, m.disk,
                m.memory_bytes, m.disk_bytes, m.rx_bytes, m.tx_bytes,
                m.uptime_seconds
            FROM systems s LEFT JOIN samples m ON m.id = (
                SELECT id FROM samples WHERE node_id=s.node_id ORDER BY id DESC LIMIT 1
            ) ORDER BY s.node_id
        """).fetchall()
    now = int(time.time())
    offline_seconds = AlertRules.from_environment().offline_seconds
    return [dict(row) | {"online": now - row["last_seen"] <= offline_seconds} for row in rows]


@app.get("/api/v1/config", dependencies=[Depends(require_admin)])
def visible_configuration(request: Request):
    rules = request.app.state.alert_rules
    return {
        "retention_days": request.app.state.retention_days,
        "alert_thresholds": {
            "cpu_percent": rules.cpu,
            "memory_percent": rules.memory,
            "disk_percent": rules.disk,
            "offline_seconds": rules.offline_seconds,
        },
        "webhook_delivery": "requires a separately configured operator worker",
    }


@app.get("/api/v1/systems", dependencies=[Depends(require_admin)])
def systems():
    return {"systems": latest_systems()}


@app.get("/api/v1/systems/{node_id}/history", dependencies=[Depends(require_admin)])
def history(node_id: str, hours: int = Query(default=24, ge=1, le=168),
            points: int = Query(default=400, ge=24, le=1000)):
    """Full-window aggregation into bounded chronological chart buckets.

    Unlike truncating to the most recent 5,000 raw samples, all samples in
    the requested interval contribute to one of <= points SQL groups. The
    database never materializes unbounded raw telemetry in Python.
    """
    if not re.fullmatch(IDENTIFIER, node_id):
        raise HTTPException(404, "Unknown system")
    now = int(time.time())
    cutoff = now - hours * 3600
    bucket_seconds = max(1, (hours * 3600 + points) // points)
    with db() as connection:
        exists = connection.execute(
            "SELECT 1 FROM systems WHERE node_id=?", (node_id,)
        ).fetchone()
        if not exists:
            raise HTTPException(404, "Unknown system")
        rows = connection.execute("""
            SELECT MAX(ts) AS ts,
                   ROUND(AVG(cpu), 3) AS cpu,
                   ROUND(AVG(memory), 3) AS memory,
                   ROUND(AVG(disk), 3) AS disk,
                   CAST(AVG(memory_bytes) AS INTEGER) AS memory_bytes,
                   CAST(AVG(disk_bytes) AS INTEGER) AS disk_bytes,
                   MAX(rx_bytes) AS rx_bytes,
                   MAX(tx_bytes) AS tx_bytes,
                   MAX(uptime_seconds) AS uptime_seconds,
                   COUNT(*) AS sample_count
            FROM samples WHERE node_id=? AND ts>=? AND ts<=?
            GROUP BY CAST((ts - ?) / ? AS INTEGER)
            ORDER BY ts DESC LIMIT ?
        """, (node_id, cutoff, now, cutoff, bucket_seconds, points)).fetchall()
    return {"node_id": node_id, "bucket_seconds": bucket_seconds,
            "samples": [dict(row) for row in reversed(rows)]}


@app.get("/api/v1/systems/{node_id}/network-rate",
         dependencies=[Depends(require_admin)])
def network_rate(node_id: str):
    """Authenticated, on-demand byte-per-second rate from two host samples."""
    if not re.fullmatch(IDENTIFIER, node_id):
        raise HTTPException(404, "Unknown system")
    with db() as connection:
        if connection.execute(
                "SELECT 1 FROM systems WHERE node_id=?", (node_id,)
        ).fetchone() is None:
            raise HTTPException(404, "Unknown system")
        readings = connection.execute(
            """SELECT ts,rx_bytes,tx_bytes,uptime_seconds FROM samples
               WHERE node_id=? ORDER BY id DESC LIMIT 2""",
            (node_id,)
        ).fetchall()
    result = {"node_id": node_id,
              "state": "insufficient_samples",
              "latest_ts": readings[0]["ts"] if readings else None,
              "interval_seconds": None,
              "rx_bytes_per_second": None,
              "tx_bytes_per_second": None}
    if len(readings) < 2:
        return result
    newer, older = readings
    delta = newer["ts"] - older["ts"]
    result["interval_seconds"] = delta if delta > 0 else None
    if delta <= 0 or delta > 3600:
        result["state"] = "invalid_interval"
        return result
    # Short counter intervals are not current throughput after the host
    # stops reporting. Respect the same configured offline window as the
    # systems overview, rather than showing an old rate as live.
    age_seconds = int(time.time()) - int(newer["ts"])
    offline_seconds = AlertRules.from_environment().offline_seconds
    if age_seconds < -5 or age_seconds > offline_seconds:
        result["state"] = "invalid_interval"
        return result
    if (newer["uptime_seconds"] < older["uptime_seconds"]
            or newer["rx_bytes"] < older["rx_bytes"]
            or newer["tx_bytes"] < older["tx_bytes"]):
        result["state"] = "counter_reset"
        return result
    result["state"] = "ok"
    result["rx_bytes_per_second"] = round((newer["rx_bytes"] - older["rx_bytes"]) / delta, 2)
    result["tx_bytes_per_second"] = round((newer["tx_bytes"] - older["tx_bytes"]) / delta, 2)
    return result

@app.get("/api/v1/systems/{node_id}/export.csv", dependencies=[Depends(require_admin)])
def export_host_csv(node_id: str, hours: int = Query(default=24, ge=1, le=8760),
                    limit: int = Query(default=1000, ge=1, le=10000),
                    before_id: int | None = Query(default=None, ge=1),
                    until_ts: int | None = Query(default=None, ge=1)):
    """Bounded owner-export of raw host samples, newest first, with cursor."""
    if not re.fullmatch(IDENTIFIER, node_id):
        raise HTTPException(404, "Unknown system")
    now = int(time.time())
    if until_ts is not None and until_ts > now:
        raise HTTPException(422, "Export window must not end in the future")
    end = now if until_ts is None else until_ts
    cutoff = end - hours * 3600
    with db() as connection:
        if connection.execute("SELECT 1 FROM systems WHERE node_id=?",
                              (node_id,)).fetchone() is None:
            raise HTTPException(404, "Unknown system")
        rows = connection.execute("""
            SELECT id, ts, cpu, memory, disk, memory_bytes, disk_bytes,
                   rx_bytes, tx_bytes, uptime_seconds
            FROM samples
            WHERE node_id=? AND ts>=? AND ts<=? AND (? IS NULL OR id<?)
            ORDER BY id DESC LIMIT ?
        """, (node_id, cutoff, end, before_id, before_id, limit + 1)).fetchall()
    has_more = len(rows) > limit
    page = rows[:limit]
    out = io.StringIO(newline="")
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(("id", "node_id", "unix_ts", "cpu_percent", "memory_percent",
                     "disk_percent", "memory_used_bytes", "disk_used_bytes",
                     "rx_bytes", "tx_bytes", "uptime_seconds"))
    for row in page:
        # Numeric conversion never permits stored spreadsheet formulas to
        # escape into exported cells, even if a DB file was modified outside
        # the Metrics API. Never echo invalid stored cell contents in errors.
        try:
            floats = [float(row[key]) for key in ("cpu", "memory", "disk", "uptime_seconds")]
            ints = [int(row[key]) for key in (
                "memory_bytes", "disk_bytes", "rx_bytes", "tx_bytes"
            )]
            id_value, ts_value = int(row["id"]), int(row["ts"])
            if not all(math.isfinite(v) for v in floats):
                raise ValueError("non-finite database value")
        except (ValueError, TypeError, OverflowError):
            raise HTTPException(500, "Metrics database contains invalid numeric data") from None
        writer.writerow((id_value, node_id, ts_value, *floats[:3], *ints, floats[3]))
    headers = {"Content-Disposition": f'attachment; filename="metrics-{node_id}.csv"',
               "X-Export-Until-Ts": str(end), "Cache-Control": "no-store"}
    if has_more and page:
        headers["X-Next-Before-Id"] = str(page[-1]["id"])
    return PlainTextResponse(out.getvalue(), media_type="text/csv; charset=utf-8",
                             headers=headers)


@app.get("/api/v1/systems/{node_id}/containers",
         dependencies=[Depends(require_admin)])
def containers(node_id: str):
    if not re.fullmatch(IDENTIFIER, node_id):
        raise HTTPException(404, "Unknown system")
    with db() as connection:
        latest = connection.execute(
            "SELECT ts FROM samples WHERE node_id=? ORDER BY id DESC LIMIT 1",
            (node_id,)
        ).fetchone()
        if latest is None:
            raise HTTPException(404, "Unknown system")
        rows = connection.execute(
            """SELECT name,cpu,memory,rx_bytes,tx_bytes,ts
            FROM container_samples WHERE node_id=? AND ts=?
            ORDER BY name LIMIT 100""",
            (node_id, latest["ts"])
        ).fetchall()
    return {"node_id": node_id, "containers": [dict(v) for v in rows]}


@app.get("/api/v1/alerts", dependencies=[Depends(require_admin)])
def alerts():
    active = evaluate(latest_systems(), AlertRules.from_environment())
    return {"alerts": active, "note": "Current-state indicators; opt-in webhook worker is separate"}


@app.get("/api/v1/alert-events", dependencies=[Depends(require_admin)])
def alert_events(limit: int = Query(default=100, ge=1, le=500)):
    with db() as connection:
        available = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='alert_events'"
        ).fetchone()
        if not available:
            return {"events": []}
        rows = connection.execute(
            """SELECT id,node_id,metric,state,message,created_ts,sent_ts,attempts
            FROM alert_events ORDER BY id DESC LIMIT ?""", (limit,)
        ).fetchall()
    return {"events": [dict(row) for row in rows]}


@app.get("/api/v1/metrics", response_class=PlainTextResponse,
         dependencies=[Depends(require_admin)])
def prometheus_metrics():
    lines = ["# GoreeCloud Metrics authenticated current host snapshot"]
    for system in latest_systems():
        label = f'node="{system["node_id"]}"'
        lines.append(f'goreecloud_agent_up{{{label}}} {int(system["online"])}')
        for metric in ("cpu", "memory", "disk"):
            if system[metric] is not None:
                lines.append(f'goreecloud_host_{metric}_percent{{{label}}} {system[metric]}')
    return "\n".join(lines) + "\n"
