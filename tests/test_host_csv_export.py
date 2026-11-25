"""Authenticated page-bounded CSV export with stable cursor and safe cells."""
from __future__ import annotations

import csv
import io
import json
import sqlite3
import time

from fastapi.testclient import TestClient
from server.app import app, db


def test_raw_csv_export_pages_and_secret_scoping(monkeypatch, tmp_path):
    path = tmp_path / "private.sqlite3"
    monkeypatch.setenv("METRICS_DB_PATH", str(path))
    monkeypatch.setenv("METRICS_ADMIN_TOKEN", "a" * 48)
    monkeypatch.setenv("METRICS_AGENT_TOKENS",
                       json.dumps({"host-a": "b" * 48, "host-b": "c" * 48}))
    now = int(time.time())
    with TestClient(app) as client:
        with db() as conn:
            conn.executemany("INSERT INTO systems VALUES(?,?,?,?)",
                             [("host-a", "Synthetic A", now-200, now),
                              ("host-b", "Synthetic B", now-200, now)])
            conn.executemany("""
                INSERT INTO samples(node_id,ts,cpu,memory,disk,memory_bytes,
                                    disk_bytes,rx_bytes,tx_bytes,uptime_seconds)
                VALUES (?,?,?,?,?,?,?,?,?,?)""",
                [("host-a", now-120+i*10, i, 10, 15, 1024, 2048, i, i+2, i*10)
                 for i in range(7)] +
                [("host-b", now-120, 88, 22, 33, 999, 999, 999, 999, 999)])
        bearer = {"Authorization": "Bearer " + "a" * 48}
        first = client.get("/api/v1/systems/host-a/export.csv?hours=24&limit=3",
                           headers=bearer)
        assert first.status_code == 200, first.text
        assert first.headers["content-type"].startswith("text/csv")
        assert first.headers["cache-control"] == "no-store"
        assert "attachment;" in first.headers["content-disposition"]
        until = first.headers["x-export-until-ts"]
        cursor = first.headers["x-next-before-id"]
        rows = list(csv.DictReader(io.StringIO(first.text)))
        assert len(rows) == 3 and rows[0]["node_id"] == "host-a"
        assert rows[0]["cpu_percent"] == "6.0"
        seen = rows
        while cursor:
            page = client.get("/api/v1/systems/host-a/export.csv",
                              params={"hours": 24, "limit": 3, "until_ts": until,
                                      "before_id": cursor},
                              headers=bearer)
            assert page.status_code == 200, page.text
            seen += list(csv.DictReader(io.StringIO(page.text)))
            cursor = page.headers.get("x-next-before-id")
        assert len(seen) == len({row["id"] for row in seen}) == 7
        assert all(row["node_id"] == "host-a" for row in seen)
        assert all(row["cpu_percent"] != "88.0" for row in seen)
        assert [int(row["cpu_percent"].split(".")[0]) for row in seen] == list(range(6,-1,-1))
        assert client.get("/api/v1/systems/host-a/export.csv").status_code == 401
        assert client.get("/api/v1/systems/host-b/export.csv",
                          headers={"Authorization": "Bearer " + "b" * 48}).status_code == 401


def test_csv_limits_and_bad_data_fail_closed(monkeypatch, tmp_path):
    path = tmp_path / "private.sqlite3"
    monkeypatch.setenv("METRICS_DB_PATH", str(path))
    monkeypatch.setenv("METRICS_ADMIN_TOKEN", "a" * 48)
    monkeypatch.setenv("METRICS_AGENT_TOKENS", json.dumps({"host-a": "b" * 48}))
    now = int(time.time())
    with TestClient(app, raise_server_exceptions=False) as client:
        with db() as conn:
            conn.execute("INSERT INTO systems VALUES(?,?,?,?)",
                         ("host-a", "Synthetic", now-60, now))
            conn.execute("""INSERT INTO samples(
                         node_id,ts,cpu,memory,disk,memory_bytes,disk_bytes,
                         rx_bytes,tx_bytes,uptime_seconds) VALUES(?,?,?,?,?,?,?,?,?,?)""",
                         ("host-a", now-10, "=HYPERLINK(1)", 10, 10, 1, 2, 3, 4, 5))
        bearer = {"Authorization": "Bearer " + "a" * 48}
        url = "/api/v1/systems/host-a/export.csv"
        for query in ("?hours=0", "?hours=8761", "?limit=0",
                      "?limit=10001", "?before_id=0", f"?until_ts={now+3600}"):
            assert client.get(url + query, headers=bearer).status_code == 422
        assert client.get("/api/v1/systems/NOT_VALID/export.csv",
                          headers=bearer).status_code == 404
        result = client.get(url, headers=bearer)
        assert result.status_code == 500
        assert "HYPERLINK" not in result.text
