#!/usr/bin/env bash
set -Eeuo pipefail

APP_DIR="${APP_DIR:-/opt/rory-trader}"
APP_USER="${APP_USER:-rory-trader}"
APP_GROUP="${APP_GROUP:-$APP_USER}"
ENV_FILE="${ENV_FILE:-$APP_DIR/.env}"
CERT_DIR="${CERT_DIR:-$APP_DIR/certs}"
CERT_FILE="${BETFAIR_CERT_FILE:-$CERT_DIR/client.crt}"
KEY_FILE="${BETFAIR_KEY_FILE:-$CERT_DIR/client.key}"
UV_BIN="${UV_BIN:-$(command -v uv || true)}"

log() {
  printf '[rory-trader-betfair] %s\n' "$*"
}

die() {
  printf '[rory-trader-betfair] ERROR: %s\n' "$*" >&2
  exit 1
}

require_root() {
  if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
    die "run this script with sudo on the Hetzner VPS"
  fi
}

prompt_if_missing() {
  local var_name="$1"
  local prompt="$2"
  local secret="${3:-false}"
  local value="${!var_name:-}"

  if [[ -n "$value" ]]; then
    return
  fi

  if [[ "$secret" == "true" ]]; then
    read -rsp "$prompt: " value
    printf '\n'
  else
    read -rp "$prompt: " value
  fi

  if [[ -z "$value" ]]; then
    die "$var_name cannot be empty"
  fi

  printf -v "$var_name" '%s' "$value"
  export "$var_name"
}

copy_secret_file() {
  local source="$1"
  local destination="$2"
  local mode="$3"

  if [[ -z "$source" ]]; then
    if [[ -f "$destination" ]]; then
      log "Preserving existing $destination"
      return
    fi
    die "missing source file for $destination"
  fi

  if [[ ! -f "$source" ]]; then
    die "source file does not exist: $source"
  fi

  install -m "$mode" -o root -g "$APP_GROUP" "$source" "$destination"
}

set_env_key() {
  local key="$1"
  local value="$2"
  local tmp

  tmp="$(mktemp)"
  touch "$ENV_FILE"

  awk -v key="$key" -v value="$value" '
    BEGIN { found = 0 }
    $0 ~ "^" key "=" {
      print key "=" value
      found = 1
      next
    }
    { print }
    END {
      if (!found) {
        print key "=" value
      }
    }
  ' "$ENV_FILE" > "$tmp"

  install -m 0640 -o root -g "$APP_GROUP" "$tmp" "$ENV_FILE"
  rm -f "$tmp"
}

run_doctor() {
  if [[ "${RUN_DOCTOR:-true}" != "true" ]]; then
    return
  fi
  if [[ -z "$UV_BIN" || ! -x "$UV_BIN" ]]; then
    log "uv was not found; skipping doctor check"
    return
  fi

  log "Running safe doctor check as $APP_USER"
  sudo -H -u "$APP_USER" "$UV_BIN" --directory "$APP_DIR" run main.py doctor
}

main() {
  require_root

  if ! id "$APP_USER" >/dev/null 2>&1; then
    die "app user $APP_USER does not exist; run deploy-hetzner-dashboard.sh first"
  fi

  install -d -m 0750 -o root -g "$APP_GROUP" "$CERT_DIR"
  install -d -m 0750 -o "$APP_USER" -g "$APP_GROUP" "$APP_DIR/runtime" "$APP_DIR/data"

  prompt_if_missing "BETFAIR_USERNAME" "Betfair username"
  prompt_if_missing "BETFAIR_PASSWORD" "Betfair password" "true"
  prompt_if_missing "BETFAIR_APP_KEY" "Betfair app key"

  copy_secret_file "${BETFAIR_CERT_SOURCE:-}" "$CERT_FILE" "0640"
  copy_secret_file "${BETFAIR_KEY_SOURCE:-}" "$KEY_FILE" "0640"

  set_env_key "BETFAIR_USERNAME" "$BETFAIR_USERNAME"
  set_env_key "BETFAIR_PASSWORD" "$BETFAIR_PASSWORD"
  set_env_key "BETFAIR_APP_KEY" "$BETFAIR_APP_KEY"
  set_env_key "BETFAIR_USE_CERT_LOGIN" "true"
  set_env_key "BETFAIR_CERT_FILE" "$CERT_FILE"
  set_env_key "BETFAIR_KEY_FILE" "$KEY_FILE"
  set_env_key "RORY_TRADER_LIVE_ENABLED" "false"
  set_env_key "RORY_TRADER_RUNTIME_ROOT" "$APP_DIR/runtime"

  chmod 0640 "$ENV_FILE" "$CERT_FILE" "$KEY_FILE"
  chown root:"$APP_GROUP" "$ENV_FILE" "$CERT_FILE" "$KEY_FILE"

  if grep -Eq '^RORY_TRADER_LIVE_ENABLED=(true|1|yes)$' "$ENV_FILE"; then
    die "$ENV_FILE enables live trading; this milestone requires RORY_TRADER_LIVE_ENABLED=false"
  fi

  log "Betfair secrets and certificate paths configured in $ENV_FILE"
  log "Certificate files are readable by $APP_USER through group $APP_GROUP and are not world-readable"
  run_doctor
}

main "$@"
