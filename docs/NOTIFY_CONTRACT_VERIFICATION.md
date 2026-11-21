# Metrics ↔ GoreeCloud Notify source-owned contract verification

The optional Metrics adapter uses the development-only GoreeCloud Notify topic contract, without requiring an administrator to disclose any real host alerts. An independent **offline-built, isolated loopback integration fixture** is available in tests/integration/notify_go_loopback.py. The fixture never clones code, installs packages, uses privileged ports or starts a persistent service on its own.

Source inspected for the initial rehearsal: GoreeCloud/notify commit 16edc051560ace6cc620b113665bceb537d4ea7e. Its go.mod contains only the Go module declaration and Go 1.23.0 requirement; it uses standard-library HTTP for the topic service. The source-owner Go handler implements POST /api/v1/topics/{topic}/messages with authenticated JSON title/body/priority fields, and GET history with bearer authentication.

An authorized operator can separately inspect the pinned source, then build its Go executable offline:

~~~sh
cd /path/to/inspected/GoreeCloud-notify
GOPROXY=off GOSUMDB=off go test ./internal/notify
GOPROXY=off GOSUMDB=off go build -o /tmp/goreecloud-notify-test ./cmd/notifyd

cd /path/to/GoreeCloud-metrics
python tests/integration/notify_go_loopback.py --notify-binary /tmp/goreecloud-notify-test
~~~

The test allocates an ephemeral local port, a new random token, and a temporary journal. It launches the supplied, pre-inspected binary as a child process with its network listener bound to 127.0.0.1, publishes only synthetic status, reads it back, ensures invalid bearer access returns 401, then terminates the child and deletes the temporary journal. No external network endpoint or webhook is accessed.

**Limits:** local HTTP is permitted solely within this disposable test fixture. The production Metrics adapter separately **requires HTTPS** for any operator-configured remote Notify origin. This test does not establish TLS trust, GoreeShield consent for real host alerts, multiuser Identity permissions, delivery guarantee under outages, a real Notify deployment or Stable acceptance.
