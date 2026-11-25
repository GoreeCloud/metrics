"""Agent failure exit codes and outbound credential redirect boundaries."""
from __future__ import annotations

import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
from agent import agent


def test_ingest_refuses_cross_origin_redirect():
    seen = []

    class Target(BaseHTTPRequestHandler):
        def do_GET(self):
            seen.append(self.headers.get("X-Agent-Token"))
            self.send_response(204)
            self.end_headers()
        def do_POST(self):
            seen.append(self.headers.get("X-Agent-Token"))
            self.send_response(204)
            self.end_headers()
        def log_message(self, *args):
            pass

    target = ThreadingHTTPServer(("127.0.0.1", 0), Target)

    class Redirector(BaseHTTPRequestHandler):
        def do_POST(self):
            self.send_response(302)
            self.send_header(
                "Location", f"http://127.0.0.1:{target.server_address[1]}/capture")
            self.end_headers()
        def log_message(self, *args):
            pass

    first = ThreadingHTTPServer(("127.0.0.1", 0), Redirector)
    threads = [threading.Thread(target=s.serve_forever, daemon=True)
               for s in (target, first)]
    try:
        for thread in threads:
            thread.start()
        with pytest.raises(ValueError, match="redirect refused"):
            agent.report(f"http://127.0.0.1:{first.server_address[1]}",
                         "s" * 48, {"node_id": "synthetic"})
        assert seen == []
    finally:
        for service in (first, target):
            service.shutdown()
            service.server_close()
        for thread in threads:
            thread.join(timeout=3)


def test_run_once_fails_nonzero_without_logging_secrets(monkeypatch, capsys):
    monkeypatch.setattr(agent, "settings", lambda: ("https://hub.example.test",
                                                    "node-a", "s" * 48))
    monkeypatch.setattr(agent, "collect", lambda node: {"node_id": node})
    monkeypatch.setattr(agent.signal, "signal", lambda *args: None)
    monkeypatch.setattr(agent.sys, "argv", ["agent", "--once"])
    monkeypatch.setattr(agent, "_STOP", False)

    def failing_send(*args):
        raise OSError("SENSITIVE_SECRET_SHOULD_NEVER_APPEAR")
    monkeypatch.setattr(agent, "report", failing_send)
    assert agent.main() == 2
    stderr = capsys.readouterr().err
    assert "Metric send failed" in stderr
    assert "SENSITIVE_SECRET" not in stderr
    assert "hub.example.test" not in stderr


def test_run_once_returns_zero_only_after_accepted_send(monkeypatch):
    sent = []
    monkeypatch.setattr(agent, "settings", lambda: ("https://hub.example.test",
                                                    "node-a", "s" * 48))
    monkeypatch.setattr(agent, "collect", lambda node: {"node_id": node})
    monkeypatch.setattr(agent, "report", lambda *args: sent.append(args))
    monkeypatch.setattr(agent.signal, "signal", lambda *args: None)
    monkeypatch.setattr(agent.sys, "argv", ["agent", "--once"])
    monkeypatch.setattr(agent, "_STOP", False)
    assert agent.main() == 0
    assert len(sent) == 1
