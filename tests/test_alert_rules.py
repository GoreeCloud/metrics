import pytest
from server.alert_rules import AlertRules, evaluate


def test_cpu_threshold_and_offline():
    systems = [
        {"node_id": "alpha", "online": True, "cpu": 85, "memory": 30, "disk": 20},
        {"node_id": "beta", "online": False, "cpu": 99, "memory": 99, "disk": 99},
    ]
    alerts = evaluate(systems, AlertRules(cpu=80))
    assert [(v["node_id"], v["metric"]) for v in alerts] == [
        ("alpha", "cpu"), ("beta", "heartbeat")
    ]


def test_invalid_configuration(monkeypatch):
    monkeypatch.setenv("METRICS_ALERT_CPU_PERCENT", "0")
    with pytest.raises(ValueError):
        AlertRules.from_environment()
    monkeypatch.setenv("METRICS_ALERT_CPU_PERCENT", "84")
    monkeypatch.setenv("METRICS_ALERT_OFFLINE_SECONDS", "invalid")
    with pytest.raises(ValueError):
        AlertRules.from_environment()
