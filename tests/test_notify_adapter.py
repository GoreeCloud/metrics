"""No live notifications are sent by these tests."""
import json
from server import notifications
from server.notify_adapter import configured_target, message_payload


def test_configuration_guardrails(monkeypatch):
    monkeypatch.setenv("METRICS_NOTIFY_BASE_URL", "https://notify.example.test")
    monkeypatch.setenv("METRICS_NOTIFY_API_TOKEN", "x" * 40)
    monkeypatch.setenv("METRICS_NOTIFY_TOPIC", "infra-alerts")
    assert configured_target()[0] == "https://notify.example.test/api/v1/topics/infra-alerts/messages"
    monkeypatch.setenv("METRICS_NOTIFY_BASE_URL", "http://127.0.0.1:8080")
    try:
        configured_target()
        assert False, "Cleartext must be refused"
    except ValueError:
        pass


def test_payload_matches_notify_contract():
    event = {"node_id": "vps-mesh", "metric": "heartbeat", "state": "firing",
             "message": "Agent offline", "created_ts": 123456}
    payload = message_payload(event)
    assert set(payload) == {"title", "body", "priority"}
    assert payload["priority"] == 5
    assert "vps-mesh" in payload["body"]


def test_delivery_uses_notify_payload(monkeypatch, tmp_path):
    monkeypatch.setenv("METRICS_DB_PATH", str(tmp_path / "events.db"))
    from server.app import init_db
    init_db()
    notifications.initialize_journal()
    notifications.record_transitions(
        [{"node_id": "vps-mesh", "metric": "cpu", "message": "CPU high"}],
        now=2_100_000_000
    )
    seen = []

    class Response:
        status = 200
        def __enter__(self): return self
        def __exit__(self, *args): return False

    class Opener:
        def open(self, request, timeout):
            seen.append({
                "payload": json.loads(request.data),
                "auth": request.get_header("Authorization"),
                "url": request.full_url,
            })
            return Response()

    monkeypatch.setattr(notifications.urllib.request, "build_opener", lambda *args: Opener())
    url = "https://notify.example.test/api/v1/topics/metrics/messages"
    assert notifications.deliver_pending(url, "x" * 40, now=2_100_000_001,
                                         notify_mode=True) == (1, 0)
    assert set(seen[0]["payload"]) == {"title", "body", "priority"}
    assert seen[0]["payload"]["priority"] == 4
    assert seen[0]["auth"] == "Bearer " + "x" * 40
    assert seen[0]["url"] == url
