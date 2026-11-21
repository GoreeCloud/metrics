# Alert thresholds and opt-in transition notifications

GoreeCloud Metrics evaluates **current-state** indicators from the latest authenticated host sample. Defaults: CPU, memory and disk each at 90%; host offline if the last heartbeat is older than 120 seconds. Configure at hub/worker startup:

~~~sh
METRICS_ALERT_CPU_PERCENT=90
METRICS_ALERT_MEMORY_PERCENT=90
METRICS_ALERT_DISK_PERCENT=90
METRICS_ALERT_OFFLINE_SECONDS=120
~~~

The optional worker `python -m server.notifications` journals *firing* and *resolved* transitions in SQLite and can forward events to an explicitly configured HTTPS webhook. Run with `--once` to verify locally without automatic scheduling. Repeated observations are deduplicated until the state resolves. Keep one worker instance, under a non-root service account, using the hub's database path and appropriate environment. No webhook is configured or contacted by default.

~~~sh
METRICS_WEBHOOK_URL=https://your-owned-https-endpoint.example/api/events
METRICS_WEBHOOK_BEARER=OPTIONAL_SECRET
python -m server.notifications --once
~~~

A webhook may disclose a node ID and active threshold to its recipient. **GoreeShield consent and destination privacy review are required before enabling one.** Requests use POST JSON, reject redirects, a bounded timeout, up to five retry attempts and a bounded exponential delay. Event delivery is at least once; duplicates can occur after a crash. The worker records up to 30 days of transitions. Actual integration with GoreeCloud Notify has *not* been verified.

Current limitations: no graphical threshold editor, incident acknowledgment, rule quiet hours, alert suppression, notification history UI or multiuser Identity auth. The worker is not automatically installed, deployed or running.
