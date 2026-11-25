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

A webhook may disclose a node ID and active threshold to its recipient. **GoreeShield consent and destination privacy review are required before enabling one.** Requests use POST JSON, reject redirects, a bounded timeout, up to five claimed attempts and a bounded exponential delay. A SQLite write-locked claim reserves each pending event before outbound HTTP for 60 seconds, so concurrently running workers cannot immediately send the same event. A crashed worker's claim expires, but exhausted attempts are not retried automatically. Delivery is best-effort with bounded retries; duplicates can occur after a crash or lease expiry. A successful send is not a guaranteed end-user notification. The worker records up to 30 days of transitions. Actual integration with GoreeCloud Notify has *not* been verified.

Current limitations: no graphical threshold editor, incident acknowledgment, rule quiet hours, alert suppression, notification history UI or multiuser Identity auth. The worker is not automatically installed, deployed or running.

## GoreeCloud Notify direct-publish adapter (optional)

An independent adapter maps alert transitions to the **currently verified GoreeCloud Notify topic-publish contract** in `GoreeCloud/notify` (Go service at `POST /api/v1/topics/{topic}/messages`). It sends only `title`, `body`, and `priority` as JSON with a separately provided bearer token.

For an authorized HTTPS deployment, set the following *privately* on the Metrics notifier worker:

~~~sh
METRICS_NOTIFY_BASE_URL=https://your-trusted-notify-origin.example
METRICS_NOTIFY_TOPIC=metrics
METRICS_NOTIFY_API_TOKEN=PASTE_NOTIFY_TOKEN_LOCALLY
~~~

The adapter refuses cleartext URLs and will reject simultaneous configuration of the generic webhook and GoreeCloud Notify. No token is stored in source. The Notify server is **not** deployed or probed automatically, and no real message delivery has been tested. GoreeShield authorization for disclosing host alert names to Notify is required. Notifications should not be treated as emergency-alert infrastructure.
