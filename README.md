# GoreeCloud Metrics

A self-hosted infrastructure monitoring platform: Python/FastAPI hub, low-privilege psutil host agent, React web dashboard, and real Flutter Linux and Android native clients. The hub–agent model is inspired by [Beszel](https://github.com/henrygd/beszel), but no Beszel source code was copied.

**Maturity: 0.1.0 development preview.** Not Stable, released, deployed, independently security-audited, signed, or physical-device validated.

## Source capabilities

- Hub: authenticated per-agent ingest, strict validation, SQLite 30-day history, basic 5-second per-node throttle, online/offline status and threshold indicators, historical reads, authenticated Prometheus-format endpoint, minimal health probe.
- Host agent: opt-in CPU, RAM, disk, network bytes-since-boot, uptime, hostname collection every 30 seconds over verified HTTPS (except localhost HTTP).
- Web: React/Vite with Recharts historical charts, systems overview, current indicators, responsive GoreeCloud UI Lagoon candidate styling.
- Linux / Android: Flutter with native Linux and Android runners, host list, utilization, CPU history chart and current indicators. Tokens held in app memory only.
- Optional deployments: systemd host agent and local-loopback Docker Compose hub; development CI and tests. Android debug APK and Linux bundle artifact uploads are configured in CI. These are development artifacts, not published releases.

**Not implemented:** Docker/Podman container metrics, in-app alert settings or native push delivery, agent enrollment UI, multiple administrator accounts/OIDC, verified centralized Identity/Mesh/Wardveil integrations, signed APK, Linux installer, backup/restore validation, production acceptance.

## Local development setup

Requirements: Python 3.12+, Node 22+, npm. Native builds require Flutter, Android SDK or the Flutter Linux toolchain.

~~~sh
git clone https://github.com/GoreeCloud/metrics.git
cd metrics
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-dev.txt
cp .env.example .env
# Replace BOTH placeholders in .env with DISTINCT cryptographically random strings.
# Generate each token with: python3 -c 'import secrets; print(secrets.token_urlsafe(48))'
set -a; . ./.env; set +a
python -m uvicorn server.app:app --host 127.0.0.1 --port 8093
~~~

On the same machine, configure the psutil agent in another shell:

~~~sh
. .venv/bin/activate
export METRICS_NODE_ID=host-a
export METRICS_HUB_URL=http://127.0.0.1:8093
export METRICS_AGENT_TOKEN='PASTE_THE_AGENT_SECRET_LOCALLY'
python -m agent.agent --once
~~~

Open the browser UI:

~~~sh
cd web
npm ci
npm run dev
# Navigate to http://127.0.0.1:5173
~~~

The development Vite server proxies same-origin API requests to port 8093. Enter the separate administrator token; it is not stored in localStorage. For deployed web clients, reverse proxy assets and /api on the same HTTPS origin.

Native applications:

~~~sh
cd apps/native
flutter pub get
flutter analyze
flutter test
flutter run -d linux
flutter build apk --debug
~~~

A generated native runner does not prove hardware acceptance. On physical Android devices, use a trusted reachable HTTPS hub.

## Alert rules and opt-in webhook worker

\`METRICS_ALERT_CPU_PERCENT\`, \`METRICS_ALERT_MEMORY_PERCENT\`, \`METRICS_ALERT_DISK_PERCENT\` and \`METRICS_ALERT_OFFLINE_SECONDS\` control current-state alert thresholds at startup. The separate \`python -m server.notifications\` process records deduplicated firing/resolved transitions in SQLite. It can deliver **opt-in** HTTPS webhook events if explicitly configured; no external delivery is enabled or deployed by default. The worker requires a single instance and appropriate DB access. See [alert operations](docs/ALERTS.md). This is not a verified GoreeCloud Notify integration.

## API

| Method | Path | Scope |
| --- | --- | --- |
| GET | /healthz | Public minimal health |
| POST | /api/v1/ingest | X-Agent-Token of registered node |
| GET | /api/v1/systems | Admin Bearer token |
| GET | /api/v1/systems/{node_id}/history?hours=24 | Admin Bearer token |
| GET | /api/v1/alerts | Admin Bearer token |
| GET | /api/v1/alert-events | Admin Bearer token; journal populated only by worker |
| GET | /api/v1/metrics | Admin Bearer token, Prometheus text |

Server timestamps override any agent clocks. Alerts are configurable current-state indicators (default >=90% CPU, RAM or disk; offline at 120 seconds). An optional separate worker records transitions and sends explicitly configured HTTPS events. The hub has no remote execution capability.

## Repository and governance

- server/: Python FastAPI hub and SQLite store
- agent/: psutil collector
- web/: React browser application
- apps/native/: Flutter native Linux and Android application
- deploy/: optional local-only container and systemd examples
- docs/: architecture, operations, security, objectives, features, roadmap
- tests/: API and agent security tests
- .github/: CI

GoreeShield owns privacy; Wardveil owns cybersecurity; GoreeCloud Mesh owns integrations; Identity owns authentication and authorization; GoreeCloud UI owns design. This early preview does not claim their runtime integrations. No external tracking is built in.

See [architecture](docs/ARCHITECTURE.md), [security](docs/SECURITY.md), [operations](docs/OPERATIONS.md), [features](docs/FEATURES.md), [objectives](docs/OBJECTIVES.md), and [roadmap](docs/ROADMAP.md).

New GoreeCloud code is MIT licensed; review [LICENSE](LICENSE) and [third-party notices](THIRD_PARTY_NOTICES.md).
