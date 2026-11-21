"""Configurable, pure alert threshold evaluation.

No persistent state or network calls are performed here.
"""
from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class AlertRules:
    cpu: float = 90.0
    memory: float = 90.0
    disk: float = 90.0
    offline_seconds: int = 120

    @classmethod
    def from_environment(cls) -> "AlertRules":
        values = {}
        for metric in ("cpu", "memory", "disk"):
            raw = os.environ.get(f"METRICS_ALERT_{metric.upper()}_PERCENT", "90")
            try:
                value = float(raw)
            except ValueError as error:
                raise ValueError(f"Invalid {metric} alert threshold") from error
            if not 1 <= value <= 100:
                raise ValueError(f"Invalid {metric} alert threshold")
            values[metric] = value
        try:
            offline = int(os.environ.get("METRICS_ALERT_OFFLINE_SECONDS", "120"))
        except ValueError as error:
            raise ValueError("Invalid offline threshold") from error
        if not 30 <= offline <= 3600:
            raise ValueError("Invalid offline threshold")
        values["offline_seconds"] = offline
        return cls(**values)


def evaluate(systems: list[dict], rules: AlertRules) -> list[dict[str, str]]:
    alerts = []
    for system in systems:
        node = system["node_id"]
        if not system["online"]:
            alerts.append({"node_id": node, "severity": "critical",
                           "metric": "heartbeat", "message": "Agent offline"})
            continue
        for metric in ("cpu", "memory", "disk"):
            reading = system.get(metric)
            threshold = getattr(rules, metric)
            if reading is not None and reading >= threshold:
                alerts.append({"node_id": node, "severity": "warning",
                               "metric": metric, "message": f"{metric} at or above {threshold:g}%"})
    return alerts
