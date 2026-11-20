#!/usr/bin/env bash
set -euo pipefail
python3 -m compileall -q agent server
python3 -m pytest -q
(cd web && npm run build)
(cd apps/native && flutter analyze && flutter test)
