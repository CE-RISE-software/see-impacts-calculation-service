#!/usr/bin/env bash
set -euo pipefail

exec python -m uvicorn see_impacts_calculation_service.app:app \
  --host "${BIND_ADDRESS:-0.0.0.0}" \
  --port "${PORT:-8080}"
