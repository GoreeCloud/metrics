"""Read-only hub diagnostics: exact schema, no secret or path disclosure."""
from __future__ import annotations

import json
import os
import sqlite3

from server import doctor
from server.app import SCHEMA_VERSION, init_db


def test_doctor_complete_nonsecret_integrity_and_counts(monkeypatch, tmp_path, capsys):
    path = tmp_path / "private-metrics-database.sqlite3"
    monkeypatch.setenv("METRICS_DB_PATH", str(path))
    init_db()
    status = doctor.check(str(path))
    assert status["status"] == "ready", status
    assert status["schema_version"] == SCHEMA_VERSION
    assert status["file_permissions_owner_only"] is True
    assert status["history_indexes_present"] is True
    assert status["host_samples"] == 0
    assert status["registered_hosts"] == 0
    assert doctor.main(["--database", str(path), "--json"]) == 0
    output = capsys.readouterr().out
    result = json.loads(output)
    assert result["status"] == "ready"
    assert "database" not in result
    assert "private-metrics" not in output


def test_doctor_rejects_missing_unknown_or_symlink_paths_without_logging_name(
        monkeypatch, tmp_path, capsys):
    secret_path = tmp_path / "HIGHLY_PRIVATE_FILENAME.sqlite3"
    assert doctor.main(["--database", str(secret_path)]) == 2
    assert "HIGHLY_PRIVATE" not in capsys.readouterr().err
    with sqlite3.connect(secret_path) as db:
        db.execute("CREATE TABLE unrelated(data TEXT)")
    assert doctor.main(["--database", str(secret_path)]) == 2
    assert "HIGHLY_PRIVATE" not in capsys.readouterr().err
    link = tmp_path / "redirect.sqlite3"
    link.symlink_to(secret_path)
    assert doctor.main(["--database", str(link)]) == 2


def test_doctor_does_not_change_permissive_file(monkeypatch, tmp_path):
    path = tmp_path / "permissive.sqlite3"
    monkeypatch.setenv("METRICS_DB_PATH", str(path))
    init_db()
    path.chmod(0o644)
    assert doctor.check(str(path))["status"] == "review_required"
    assert doctor.main(["--database", str(path)]) == 2
    assert (path.stat().st_mode & 0o777) == 0o644


def test_doctor_rejects_future_schema_without_overwriting(monkeypatch, tmp_path):
    path = tmp_path / "future.sqlite3"
    monkeypatch.setenv("METRICS_DB_PATH", str(path))
    init_db()
    with sqlite3.connect(path) as conn:
        conn.execute("PRAGMA user_version=92")
    assert doctor.check(str(path))["status"] == "review_required"
    assert doctor.main(["--database", str(path), "--json"]) == 2
    with sqlite3.connect(path) as conn:
        assert conn.execute("PRAGMA user_version").fetchone()[0] == 92
