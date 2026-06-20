#!/usr/bin/env bash
set -Eeuo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CATEGORY="${1:-${BETFAIR_MARKETS_CATEGORY:-sports}}"
MAX_RESULTS="${2:-${BETFAIR_MARKETS_MAX_RESULTS:-25}}"
UV_BIN="${UV_BIN:-$(command -v uv || true)}"
SESSION_TIMEOUT_SECONDS="${RORY_TRADER_PAPER_SESSION_TIMEOUT_SECONDS:-${PAPER_SESSION_TIMEOUT_SECONDS:-300}}"

die() {
  printf '[rory-trader-paper] ERROR: %s\n' "$*" >&2
  exit 1
}

cd "$REPO_DIR"

if [[ "${RORY_TRADER_LIVE_ENABLED:-false}" =~ ^(true|1|yes)$ ]]; then
  die "RORY_TRADER_LIVE_ENABLED is true in the process environment"
fi

if [[ -f ".env" ]] && grep -Eq '^RORY_TRADER_LIVE_ENABLED=(true|1|yes)$' ".env"; then
  die ".env enables live trading; paper sessions require RORY_TRADER_LIVE_ENABLED=false"
fi

if [[ -z "$UV_BIN" || ! -x "$UV_BIN" ]]; then
  die "uv was not found in PATH"
fi

if command -v timeout >/dev/null 2>&1; then
  timeout "$SESSION_TIMEOUT_SECONDS" "$UV_BIN" run main.py paper "$CATEGORY" "$MAX_RESULTS"
else
  "$UV_BIN" run main.py paper "$CATEGORY" "$MAX_RESULTS"
fi
