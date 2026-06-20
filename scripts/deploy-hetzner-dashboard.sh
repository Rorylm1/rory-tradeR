#!/usr/bin/env bash
set -Eeuo pipefail

APP_DIR="${APP_DIR:-/opt/rory-trader}"
APP_USER="${APP_USER:-rory-trader}"
APP_GROUP="${APP_GROUP:-$APP_USER}"
APP_HOME="${APP_HOME:-/var/lib/rory-trader}"
REPO_URL="${REPO_URL:-https://github.com/Rorylm1/rory-tradeR.git}"
REPO_BRANCH="${REPO_BRANCH:-main}"
HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8000}"
SERVICE_NAME="${SERVICE_NAME:-rory-trader-dashboard}"
PAPER_SERVICE_NAME="${PAPER_SERVICE_NAME:-rory-trader-paper-session}"
PAPER_TIMER_NAME="${PAPER_TIMER_NAME:-${PAPER_SERVICE_NAME}.timer}"
PAPER_TIMER_ENABLED="${PAPER_TIMER_ENABLED:-auto}"
PAPER_TIMER_ON_CALENDAR="${PAPER_TIMER_ON_CALENDAR:-*:0/15}"
PAPER_TIMER_RANDOMIZED_DELAY_SEC="${PAPER_TIMER_RANDOMIZED_DELAY_SEC:-60}"
PAPER_SESSION_TIMEOUT_SECONDS="${PAPER_SESSION_TIMEOUT_SECONDS:-300}"
PAPER_CATEGORY="${PAPER_CATEGORY:-sports}"
PAPER_MAX_RESULTS="${PAPER_MAX_RESULTS:-25}"
ENV_FILE="${ENV_FILE:-$APP_DIR/.env}"
CADDY_DROPIN="${CADDY_DROPIN:-/etc/caddy/conf.d/rory-trader-dashboard.caddy}"
UV_SYNC_ARGS="${UV_SYNC_ARGS:---group dev}"

API_DOMAIN="${API_DOMAIN:-}"
VERCEL_ORIGIN="${VERCEL_ORIGIN:-}"
DASHBOARD_TOKEN="${RORY_TRADER_DASHBOARD_TOKEN:-}"

log() {
  printf '[rory-trader-deploy] %s\n' "$*"
}

die() {
  printf '[rory-trader-deploy] ERROR: %s\n' "$*" >&2
  exit 1
}

require_root() {
  if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
    die "run this script with sudo on the Hetzner VPS"
  fi
}

usage() {
  cat <<'USAGE'
Usage:
  sudo API_DOMAIN=api.example.com \
    VERCEL_ORIGIN=https://your-vercel-app.vercel.app \
    bash scripts/deploy-hetzner-dashboard.sh

Environment:
  APP_DIR                         default: /opt/rory-trader
  APP_USER                        default: rory-trader
  REPO_URL                        default: https://github.com/Rorylm1/rory-tradeR.git
  REPO_BRANCH                     default: main
  HOST                            default: 127.0.0.1
  PORT                            default: 8000
  API_DOMAIN                      optional; configures Caddy when set
  VERCEL_ORIGIN                   optional but recommended for dashboard CORS
  RORY_TRADER_DASHBOARD_TOKEN     optional; generated if missing
  PAPER_TIMER_ENABLED             auto, true, or false; default: auto
  PAPER_TIMER_ON_CALENDAR         systemd OnCalendar value; default: *:0/15
  PAPER_SESSION_TIMEOUT_SECONDS   one-shot paper service timeout; default: 300

Secrets are written only to APP_DIR/.env on the VPS and are not echoed.
USAGE
}

install_packages() {
  if ! command -v apt-get >/dev/null 2>&1; then
    die "this deployment script expects Ubuntu/Debian with apt-get"
  fi

  log "Installing base packages"
  apt-get update
  DEBIAN_FRONTEND=noninteractive apt-get install -y git curl ca-certificates caddy openssl sudo
}

install_uv() {
  if command -v uv >/dev/null 2>&1; then
    UV_BIN="$(command -v uv)"
    export UV_BIN
    log "Using uv at $UV_BIN"
    return
  fi

  log "Installing uv into /usr/local/bin"
  curl -LsSf https://astral.sh/uv/install.sh | env UV_INSTALL_DIR=/usr/local/bin sh

  if [[ ! -x /usr/local/bin/uv ]]; then
    die "uv install did not create /usr/local/bin/uv"
  fi

  UV_BIN="/usr/local/bin/uv"
  export UV_BIN
}

ensure_app_user() {
  if id "$APP_USER" >/dev/null 2>&1; then
    log "Using existing user $APP_USER"
  else
    log "Creating system user $APP_USER"
    useradd --system --create-home --home-dir "$APP_HOME" --shell /usr/sbin/nologin "$APP_USER"
  fi

  install -d -o "$APP_USER" -g "$APP_GROUP" "$APP_HOME"
}

as_app_user() {
  sudo -H -u "$APP_USER" "$@"
}

checkout_repo() {
  if [[ -d "$APP_DIR/.git" ]]; then
    log "Updating existing checkout in $APP_DIR"
    as_app_user git -C "$APP_DIR" fetch origin "$REPO_BRANCH"
    as_app_user git -C "$APP_DIR" pull --ff-only origin "$REPO_BRANCH"
    return
  fi

  if [[ -e "$APP_DIR" && -n "$(find "$APP_DIR" -mindepth 1 -maxdepth 1 -print -quit 2>/dev/null)" ]]; then
    die "$APP_DIR exists and is not an empty git checkout"
  fi

  log "Cloning $REPO_URL into $APP_DIR"
  install -d -o "$APP_USER" -g "$APP_GROUP" "$APP_DIR"
  as_app_user git clone --branch "$REPO_BRANCH" "$REPO_URL" "$APP_DIR"
}

sync_python_env() {
  log "Installing Python dependencies with uv"
  as_app_user "$UV_BIN" --directory "$APP_DIR" sync $UV_SYNC_ARGS
}

random_token() {
  openssl rand -hex 32
}

env_has_key() {
  local key="$1"
  [[ -f "$ENV_FILE" ]] && grep -Eq "^${key}=" "$ENV_FILE"
}

env_value() {
  local key="$1"
  [[ -f "$ENV_FILE" ]] || return 0
  awk -F= -v key="$key" '$1 == key { print substr($0, index($0, "=") + 1); exit }' "$ENV_FILE"
}

append_env_key() {
  local key="$1"
  local value="$2"
  printf '%s=%s\n' "$key" "$value" >> "$ENV_FILE"
}

create_or_update_env() {
  install -d -o "$APP_USER" -g "$APP_GROUP" "$APP_DIR"
  install -d -o "$APP_USER" -g "$APP_GROUP" "$APP_DIR/runtime" "$APP_DIR/data"
  install -d -m 0750 -o root -g "$APP_GROUP" "$APP_DIR/certs"

  if [[ -z "$DASHBOARD_TOKEN" ]]; then
    DASHBOARD_TOKEN="$(random_token)"
  fi

  if [[ ! -f "$ENV_FILE" ]]; then
    log "Creating $ENV_FILE"
    umask 077
    cat > "$ENV_FILE" <<EOF
BETFAIR_USERNAME=${BETFAIR_USERNAME:-}
BETFAIR_PASSWORD=${BETFAIR_PASSWORD:-}
BETFAIR_APP_KEY=${BETFAIR_APP_KEY:-}
BETFAIR_USE_CERT_LOGIN=${BETFAIR_USE_CERT_LOGIN:-true}
BETFAIR_CERT_FILE=${BETFAIR_CERT_FILE:-$APP_DIR/certs/client.crt}
BETFAIR_KEY_FILE=${BETFAIR_KEY_FILE:-$APP_DIR/certs/client.key}
RORY_TRADER_RUNTIME_ROOT=${RORY_TRADER_RUNTIME_ROOT:-$APP_DIR/runtime}
RORY_TRADER_LIVE_ENABLED=false
RORY_TRADER_DASHBOARD_TOKEN=$DASHBOARD_TOKEN
RORY_TRADER_DASHBOARD_ALLOWED_ORIGINS=$VERCEL_ORIGIN
RORY_TRADER_DASHBOARD_STALE_AFTER_SECONDS=${RORY_TRADER_DASHBOARD_STALE_AFTER_SECONDS:-1800}
RORY_TRADER_PAPER_COMMISSION_RATE=${RORY_TRADER_PAPER_COMMISSION_RATE:-0.02}
RORY_TRADER_PAPER_SLIPPAGE_BPS=${RORY_TRADER_PAPER_SLIPPAGE_BPS:-25}
RORY_TRADER_MAX_STAKE_PER_TRADE=${RORY_TRADER_MAX_STAKE_PER_TRADE:-10}
RORY_TRADER_MAX_MARKET_EXPOSURE=${RORY_TRADER_MAX_MARKET_EXPOSURE:-20}
RORY_TRADER_MAX_DAILY_LOSS=${RORY_TRADER_MAX_DAILY_LOSS:-20}
RORY_TRADER_PAPER_MAX_SNAPSHOT_AGE_SECONDS=${RORY_TRADER_PAPER_MAX_SNAPSHOT_AGE_SECONDS:-1800}
RORY_TRADER_PAPER_MIN_AVAILABLE_SIZE=${RORY_TRADER_PAPER_MIN_AVAILABLE_SIZE:-2}
EOF
  else
    log "Preserving existing $ENV_FILE"
    if ! env_has_key "RORY_TRADER_LIVE_ENABLED"; then
      append_env_key "RORY_TRADER_LIVE_ENABLED" "false"
    fi
    if ! env_has_key "RORY_TRADER_DASHBOARD_TOKEN"; then
      append_env_key "RORY_TRADER_DASHBOARD_TOKEN" "$DASHBOARD_TOKEN"
    fi
    if [[ -n "$VERCEL_ORIGIN" ]] && ! env_has_key "RORY_TRADER_DASHBOARD_ALLOWED_ORIGINS"; then
      append_env_key "RORY_TRADER_DASHBOARD_ALLOWED_ORIGINS" "$VERCEL_ORIGIN"
    fi
    if ! env_has_key "RORY_TRADER_RUNTIME_ROOT"; then
      append_env_key "RORY_TRADER_RUNTIME_ROOT" "$APP_DIR/runtime"
    fi
    if ! env_has_key "RORY_TRADER_PAPER_COMMISSION_RATE"; then
      append_env_key "RORY_TRADER_PAPER_COMMISSION_RATE" "0.02"
    fi
    if ! env_has_key "RORY_TRADER_PAPER_SLIPPAGE_BPS"; then
      append_env_key "RORY_TRADER_PAPER_SLIPPAGE_BPS" "25"
    fi
    if ! env_has_key "RORY_TRADER_MAX_STAKE_PER_TRADE"; then
      append_env_key "RORY_TRADER_MAX_STAKE_PER_TRADE" "10"
    fi
    if ! env_has_key "RORY_TRADER_MAX_MARKET_EXPOSURE"; then
      append_env_key "RORY_TRADER_MAX_MARKET_EXPOSURE" "20"
    fi
    if ! env_has_key "RORY_TRADER_MAX_DAILY_LOSS"; then
      append_env_key "RORY_TRADER_MAX_DAILY_LOSS" "20"
    fi
    if ! env_has_key "RORY_TRADER_PAPER_MAX_SNAPSHOT_AGE_SECONDS"; then
      append_env_key "RORY_TRADER_PAPER_MAX_SNAPSHOT_AGE_SECONDS" "1800"
    fi
    if ! env_has_key "RORY_TRADER_PAPER_MIN_AVAILABLE_SIZE"; then
      append_env_key "RORY_TRADER_PAPER_MIN_AVAILABLE_SIZE" "2"
    fi
  fi

  chown root:"$APP_GROUP" "$ENV_FILE"
  chmod 0640 "$ENV_FILE"
  chown -R "$APP_USER":"$APP_GROUP" "$APP_DIR/runtime" "$APP_DIR/data"

  if grep -Eq '^RORY_TRADER_LIVE_ENABLED=(true|1|yes)$' "$ENV_FILE"; then
    die "$ENV_FILE enables live trading; set RORY_TRADER_LIVE_ENABLED=false before starting the service"
  fi

  if [[ -z "$VERCEL_ORIGIN" ]]; then
    log "VERCEL_ORIGIN was not set; add RORY_TRADER_DASHBOARD_ALLOWED_ORIGINS before connecting Vercel"
  fi
}

install_systemd_service() {
  local unit_path="/etc/systemd/system/${SERVICE_NAME}.service"

  log "Writing systemd service $unit_path"
  cat > "$unit_path" <<EOF
[Unit]
Description=Rory TradeR Dashboard API
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=$APP_DIR
EnvironmentFile=$ENV_FILE
ExecStart=$UV_BIN run main.py dashboard-api $HOST $PORT
Restart=on-failure
RestartSec=5
User=$APP_USER
Group=$APP_GROUP
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=full
ReadWritePaths=$APP_DIR/runtime $APP_DIR/certs

[Install]
WantedBy=multi-user.target
EOF

  systemctl daemon-reload
  systemctl enable "$SERVICE_NAME"
  systemctl restart "$SERVICE_NAME"
}

install_paper_session_service() {
  local unit_path="/etc/systemd/system/${PAPER_SERVICE_NAME}.service"
  local timer_path="/etc/systemd/system/${PAPER_TIMER_NAME}"

  log "Writing bounded one-shot paper service $unit_path"
  cat > "$unit_path" <<EOF
[Unit]
Description=Rory TradeR One-Shot Paper Session
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
WorkingDirectory=$APP_DIR
EnvironmentFile=$ENV_FILE
ExecStart=$APP_DIR/scripts/run-paper-session.sh $PAPER_CATEGORY $PAPER_MAX_RESULTS
User=$APP_USER
Group=$APP_GROUP
TimeoutStartSec=$PAPER_SESSION_TIMEOUT_SECONDS
StandardOutput=journal
StandardError=journal
SyslogIdentifier=$PAPER_SERVICE_NAME
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=full
ReadWritePaths=$APP_DIR/runtime $APP_DIR/data
EOF

  log "Writing paper timer $timer_path"
  cat > "$timer_path" <<EOF
[Unit]
Description=Run Rory TradeR paper session on a bounded recurring schedule

[Timer]
OnCalendar=$PAPER_TIMER_ON_CALENDAR
RandomizedDelaySec=$PAPER_TIMER_RANDOMIZED_DELAY_SEC
Persistent=false
Unit=$PAPER_SERVICE_NAME.service

[Install]
WantedBy=timers.target
EOF

  systemctl daemon-reload

  if should_enable_paper_timer; then
    log "Enabling paper timer $PAPER_TIMER_NAME"
    systemctl enable --now "$PAPER_TIMER_NAME"
  else
    log "Paper timer installed but not enabled"
    systemctl disable --now "$PAPER_TIMER_NAME" >/dev/null 2>&1 || true
  fi
}

has_betfair_config() {
  local username password app_key use_cert cert_file key_file
  username="$(env_value BETFAIR_USERNAME)"
  password="$(env_value BETFAIR_PASSWORD)"
  app_key="$(env_value BETFAIR_APP_KEY)"
  use_cert="$(env_value BETFAIR_USE_CERT_LOGIN | tr '[:upper:]' '[:lower:]')"
  cert_file="$(env_value BETFAIR_CERT_FILE)"
  key_file="$(env_value BETFAIR_KEY_FILE)"

  [[ -n "$username" && -n "$password" && -n "$app_key" ]] || return 1
  if [[ "$use_cert" =~ ^(true|1|yes)$ ]]; then
    [[ -f "$cert_file" && -f "$key_file" ]] || return 1
  fi
  return 0
}

should_enable_paper_timer() {
  case "$(printf '%s' "$PAPER_TIMER_ENABLED" | tr '[:upper:]' '[:lower:]')" in
    true|1|yes)
      return 0
      ;;
    false|0|no)
      return 1
      ;;
    auto|"")
      has_betfair_config
      return $?
      ;;
    *)
      die "PAPER_TIMER_ENABLED must be auto, true, or false"
      ;;
  esac
}

configure_caddy() {
  if [[ -z "$API_DOMAIN" ]]; then
    log "API_DOMAIN was not set; skipping Caddy site configuration"
    return
  fi

  log "Configuring Caddy reverse proxy for $API_DOMAIN"
  install -d /etc/caddy/conf.d
  cat > "$CADDY_DROPIN" <<EOF
$API_DOMAIN {
  reverse_proxy $HOST:$PORT
}
EOF

  if [[ ! -f /etc/caddy/Caddyfile ]]; then
    printf 'import /etc/caddy/conf.d/*.caddy\n' > /etc/caddy/Caddyfile
  elif ! grep -Eq '^[[:space:]]*import[[:space:]]+/etc/caddy/conf\.d/\*\.caddy' /etc/caddy/Caddyfile; then
    cp /etc/caddy/Caddyfile "/etc/caddy/Caddyfile.$(date +%Y%m%d%H%M%S).bak"
    printf '\nimport /etc/caddy/conf.d/*.caddy\n' >> /etc/caddy/Caddyfile
  fi

  caddy fmt --overwrite "$CADDY_DROPIN"
  caddy validate --config /etc/caddy/Caddyfile
  systemctl reload caddy
}

show_next_steps() {
  log "Deployment complete"
  log "Check service: sudo systemctl status $SERVICE_NAME"
  log "Check logs: sudo journalctl -u $SERVICE_NAME -f"

  if [[ -n "$API_DOMAIN" ]]; then
    log "Set Vercel TRADER_BACKEND_URL=https://$API_DOMAIN"
    log "Unauthenticated health check should fail: curl -i https://$API_DOMAIN/api/health"
    log "Token-authenticated health check: curl -i -H 'X-Rory-Dashboard-Token: <token-from-$ENV_FILE>' https://$API_DOMAIN/api/health"
  else
    log "Set Vercel TRADER_BACKEND_URL to the HTTPS URL you place in front of this API"
    log "Local health check: curl -i -H 'X-Rory-Dashboard-Token: <token-from-$ENV_FILE>' http://$HOST:$PORT/api/health"
  fi

  log "Set Vercel TRADER_BACKEND_TOKEN to the same token stored in $ENV_FILE"
  log "Set Vercel DASHBOARD_BASIC_AUTH_USER and DASHBOARD_BASIC_AUTH_PASSWORD before exposing the dashboard"
  log "Run one paper session manually: sudo systemctl start $PAPER_SERVICE_NAME"
  log "Check recurring paper loop: sudo systemctl status $PAPER_TIMER_NAME && sudo systemctl list-timers '$PAPER_TIMER_NAME'"
  log "Disable recurring paper loop: sudo systemctl disable --now $PAPER_TIMER_NAME"
}

main() {
  if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
    usage
    exit 0
  fi

  require_root
  install_packages
  install_uv
  ensure_app_user
  checkout_repo
  sync_python_env
  create_or_update_env
  install_systemd_service
  install_paper_session_service
  configure_caddy
  show_next_steps
}

main "$@"
