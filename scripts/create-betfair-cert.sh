#!/usr/bin/env bash
set -Eeuo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CERT_DIR="${CERT_DIR:-$REPO_DIR/runtime/betfair/certs}"
BASENAME="${BASENAME:-client-2048}"
DAYS="${DAYS:-365}"
COMMON_NAME="${COMMON_NAME:-rory-trader-betfair}"
KEY_FILE="${BETFAIR_KEY_FILE:-$CERT_DIR/$BASENAME.key}"
CERT_FILE="${BETFAIR_CERT_FILE:-$CERT_DIR/$BASENAME.crt}"
ENV_FILE="${ENV_FILE:-$REPO_DIR/.env}"
FORCE=false
WRITE_ENV=false

usage() {
  cat <<'EOF'
Usage: scripts/create-betfair-cert.sh [--write-env] [--force]

Generates a project-local 2048-bit RSA client certificate/key pair for
Betfair non-interactive login. Upload the generated .crt file to Betfair,
keep the .key file local and secret, then run `uv run main.py doctor`.

Options:
  --write-env  Set BETFAIR_USE_CERT_LOGIN, BETFAIR_CERT_FILE, and BETFAIR_KEY_FILE in .env.
  --force      Replace existing generated cert/key files.
EOF
}

die() {
  printf '[rory-trader-cert] ERROR: %s\n' "$*" >&2
  exit 1
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

  install -m 0600 "$tmp" "$ENV_FILE"
  rm -f "$tmp"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --write-env)
      WRITE_ENV=true
      shift
      ;;
    --force)
      FORCE=true
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      die "unknown argument: $1"
      ;;
  esac
done

command -v openssl >/dev/null 2>&1 || die "openssl is required"

if [[ "$FORCE" != "true" && ( -e "$KEY_FILE" || -e "$CERT_FILE" ) ]]; then
  die "cert/key already exists; pass --force to replace: $CERT_FILE $KEY_FILE"
fi

install -d -m 0700 "$CERT_DIR"

config_file="$(mktemp)"
cleanup() {
  rm -f "$config_file"
}
trap cleanup EXIT

cat > "$config_file" <<EOF
[ req ]
distinguished_name = req_distinguished_name
prompt = no
x509_extensions = ssl_client

[ req_distinguished_name ]
CN = $COMMON_NAME

[ ssl_client ]
basicConstraints = CA:FALSE
keyUsage = digitalSignature, keyEncipherment
extendedKeyUsage = clientAuth
EOF

openssl genrsa -out "$KEY_FILE" 2048 >/dev/null 2>&1
chmod 0600 "$KEY_FILE"

openssl req \
  -new \
  -x509 \
  -key "$KEY_FILE" \
  -out "$CERT_FILE" \
  -days "$DAYS" \
  -sha256 \
  -config "$config_file" >/dev/null 2>&1
chmod 0644 "$CERT_FILE"

if [[ "$WRITE_ENV" == "true" ]]; then
  set_env_key "BETFAIR_USE_CERT_LOGIN" "true"
  set_env_key "BETFAIR_CERT_FILE" "$CERT_FILE"
  set_env_key "BETFAIR_KEY_FILE" "$KEY_FILE"
fi

printf '[rory-trader-cert] generated public certificate: %s\n' "$CERT_FILE"
printf '[rory-trader-cert] generated private key: %s\n' "$KEY_FILE"
openssl x509 -in "$CERT_FILE" -noout -subject -dates -fingerprint -sha256
printf '\nNext:\n'
printf '1. Upload the .crt file to Betfair under your API/certificate settings.\n'
printf '2. Keep the .key file private; it is project-local runtime state and must not be committed.\n'
printf '3. Run: uv run main.py doctor\n'
printf '4. Once doctor is OK, run: uv run main.py paper tennis 100\n'
