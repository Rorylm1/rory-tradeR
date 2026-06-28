# Hetzner VPS + Vercel Dashboard Deployment

This deployment keeps Betfair credentials on a Hetzner VPS and uses Vercel only for the dashboard UI.

## Current Deployment

- Dashboard URL: `https://rory-trade-r.vercel.app`
- Hetzner VPS IPv4: `46.62.217.82`
- VPS app directory: `/opt/rory-trader`
- Dashboard API service: `rory-trader-dashboard`
- One-shot paper service: `rory-trader-paper-session`
- Recurring paper timer: `rory-trader-paper-session.timer`
- Betfair cert login status on `2026-06-20`: `SUCCESS`
- Latest verified dashboard state on `2026-06-20`: Betfair ready, data fresh, live disabled
- Latest timer-verified paper session on `2026-06-20T18:30:46Z` collected 25 live Betfair snapshots and
  created 0 paper fills because the strategy filters found no eligible trades
- Latest recurring timer state on `2026-06-20T18:31:43Z`: active and enabled; previous run
  `2026-06-20T18:30:43Z`, next run `2026-06-20T18:45:52Z`
- Next infrastructure tidy-up: put an HTTPS domain in front of the VPS API and update Vercel `TRADER_BACKEND_URL`

## Architecture

- Hetzner VPS: `uv` Python app, FastAPI dashboard API, SQLite, Betfair credentials, paper journal.
- Vercel: Next.js dashboard and HTTP Basic auth.
- Browser: talks to Vercel only.
- Vercel: talks to the VPS API using `X-Rory-Dashboard-Token`.
- VPS: talks to Betfair and local runtime state.

Live execution remains disabled in this milestone. The dashboard records review status only.

## Hetzner Server

Recommended first server:

- EU region
- Ubuntu 24.04 LTS
- at least 2 vCPU, 4 GB RAM, 40 GB disk
- SSH key login only
- public IPv4 enabled
- firewall ports: `22`, `80`, `443`

Automated Bash deployment:

```bash
curl -fsSL \
  https://raw.githubusercontent.com/Rorylm1/rory-tradeR/main/scripts/deploy-hetzner-dashboard.sh \
  -o /tmp/deploy-hetzner-dashboard.sh

sudo API_DOMAIN=api.your-domain.example \
  VERCEL_ORIGIN=https://<your-vercel-app>.vercel.app \
  bash /tmp/deploy-hetzner-dashboard.sh
```

The script installs system packages, installs `uv`, clones or fast-forwards the repo in `/opt/rory-trader`,
creates the VPS-only `.env` when missing, installs the dashboard `systemd` service, installs a bounded
one-shot paper-session service plus an explicit timer, and configures a Caddy reverse proxy when `API_DOMAIN` is set. It does not
print dashboard tokens or Betfair credentials.

The paper timer defaults to `PAPER_TIMER_ENABLED=auto`: it is enabled only when Betfair credentials are already present
and any configured certificate files exist. Set `PAPER_TIMER_ENABLED=true` to force-enable it during a known-good deploy,
or `PAPER_TIMER_ENABLED=false` to install it without enabling recurrence.

The manual equivalent is:

Install baseline packages:

```bash
sudo apt update
sudo apt install -y git curl ca-certificates caddy
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Clone and install:

```bash
git clone https://github.com/Rorylm1/rory-tradeR.git
cd rory-tradeR
uv sync --group dev
```

Create `.env` on the VPS only:

```bash
BETFAIR_USERNAME=
BETFAIR_PASSWORD=
BETFAIR_APP_KEY=
BETFAIR_USE_CERT_LOGIN=true
BETFAIR_CERT_FILE=/opt/rory-trader/runtime/betfair/certs/client.crt
BETFAIR_KEY_FILE=/opt/rory-trader/runtime/betfair/certs/client.key
RORY_TRADER_LIVE_ENABLED=false
RORY_TRADER_DASHBOARD_TOKEN=<long-random-token>
RORY_TRADER_DASHBOARD_ALLOWED_ORIGINS=https://<your-vercel-app>.vercel.app
RORY_TRADER_DASHBOARD_STALE_AFTER_SECONDS=1800
RORY_TRADER_PAPER_COMMISSION_RATE=0.02
RORY_TRADER_PAPER_SLIPPAGE_BPS=25
RORY_TRADER_MAX_STAKE_PER_TRADE=10
RORY_TRADER_MAX_MARKET_EXPOSURE=20
RORY_TRADER_MAX_DAILY_LOSS=20
RORY_TRADER_PAPER_MAX_SNAPSHOT_AGE_SECONDS=1800
RORY_TRADER_PAPER_MIN_AVAILABLE_SIZE=2
RORY_TRADER_PAPER_SESSION_TIMEOUT_SECONDS=300
RORY_TRADER_BETFAIR_TENNIS_MARKET_TYPES=MATCH_ODDS,SET_WINNER
RORY_TRADER_BETFAIR_TENNIS_MIN_START_MINUTES=30
RORY_TRADER_BETFAIR_TENNIS_MAX_START_HOURS=72
BETFAIR_MARKETS_CATEGORY=tennis
BETFAIR_MARKETS_MAX_RESULTS=100
```

Start locally on the VPS:

```bash
uv run main.py dashboard-api 127.0.0.1 8000
```

## systemd Service

Create `/etc/systemd/system/rory-trader-dashboard.service`:

```ini
[Unit]
Description=Rory TradeR Dashboard API
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=/opt/rory-trader
EnvironmentFile=/opt/rory-trader/.env
ExecStart=/root/.local/bin/uv run main.py dashboard-api 127.0.0.1 8000
Restart=on-failure
RestartSec=5
User=root

[Install]
WantedBy=multi-user.target
```

Enable it:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now rory-trader-dashboard
sudo systemctl status rory-trader-dashboard
```

## Paper Service And Timer

Create `/etc/systemd/system/rory-trader-paper-session.service`:

```ini
[Unit]
Description=Rory TradeR One-Shot Paper Session
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
WorkingDirectory=/opt/rory-trader
EnvironmentFile=/opt/rory-trader/.env
ExecStart=/opt/rory-trader/scripts/run-paper-session.sh tennis 100
User=rory-trader
Group=rory-trader
TimeoutStartSec=300
StandardOutput=journal
StandardError=journal
SyslogIdentifier=rory-trader-paper-session
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=full
ReadWritePaths=/opt/rory-trader/runtime /opt/rory-trader/data
```

Create `/etc/systemd/system/rory-trader-paper-session.timer`:

```ini
[Unit]
Description=Run Rory TradeR paper session on a bounded recurring schedule

[Timer]
OnCalendar=*:0/15
RandomizedDelaySec=60
Persistent=false
Unit=rory-trader-paper-session.service

[Install]
WantedBy=timers.target
```

Operate it:

```bash
sudo systemctl start rory-trader-paper-session
sudo systemctl enable --now rory-trader-paper-session.timer
sudo systemctl list-timers rory-trader-paper-session.timer
sudo journalctl -u rory-trader-paper-session -n 80 --no-pager
sudo systemctl disable --now rory-trader-paper-session.timer
```

The timer is deliberately paper-only. `scripts/run-paper-session.sh` refuses to run if `RORY_TRADER_LIVE_ENABLED`
is true and the Betfair adapter reports `supports_live_execution: false`.

## Caddy

Example Caddy site:

```caddyfile
api.your-domain.example {
  reverse_proxy 127.0.0.1:8000
}
```

Reload:

```bash
sudo caddy reload
```

## Vercel

Deploy the `web/` directory as the Vercel project.

Use an HTTPS API domain for `TRADER_BACKEND_URL` before exposing the deployed dashboard. The raw VPS IP is useful
for SSH and local smoke checks, but avoid sending `TRADER_BACKEND_TOKEN` over plain HTTP.

Set Vercel environment variables:

```bash
DASHBOARD_BASIC_AUTH_ENABLED=true
DASHBOARD_BASIC_AUTH_USER=rory
DASHBOARD_BASIC_AUTH_PASSWORD=<long-random-password>
DASHBOARD_PUBLIC_READ_ONLY=false
TRADER_BACKEND_URL=https://api.your-domain.example
TRADER_BACKEND_TOKEN=<same value as RORY_TRADER_DASHBOARD_TOKEN>
```

Do not add Betfair credentials to Vercel.

To temporarily make the dashboard public while staying read-only, leave `DASHBOARD_BASIC_AUTH_ENABLED` unset or set
it to `false`. In that mode the browser Basic Auth prompt is skipped and Vercel rejects proxied non-GET dashboard
requests. The public proof view also hides operator-only paper-session controls. To restore the prompt, set
`DASHBOARD_BASIC_AUTH_ENABLED=true` with both username and password configured.

## Betfair Credentials And Certs

Keep Betfair secrets and project-local runtime certificate files on the VPS only. Upload the `.crt` and `.key` files
to a temporary location first, then run the credential setup script:

```bash
scp client.crt client.key root@46.62.217.82:/tmp/

ssh root@46.62.217.82

sudo BETFAIR_CERT_SOURCE=/tmp/client.crt \
  BETFAIR_KEY_SOURCE=/tmp/client.key \
  bash /opt/rory-trader/scripts/configure-betfair-vps.sh

rm -f /tmp/client.crt /tmp/client.key
```

The script prompts for the Betfair username, password, and app key without writing them to shell history,
copies certs into `/opt/rory-trader/runtime/betfair/certs/`, stores paths in `/opt/rory-trader/.env`, forces
`RORY_TRADER_LIVE_ENABLED=false`, and runs `doctor`.

Expected file permissions:

```bash
sudo ls -l /opt/rory-trader/.env /opt/rory-trader/runtime/betfair/certs/
```

- `/opt/rory-trader/.env`: `0640`, owned by `root:rory-trader`
- `/opt/rory-trader/runtime/betfair/certs/client.crt`: `0640`, owned by `root:rory-trader`
- `/opt/rory-trader/runtime/betfair/certs/client.key`: `0640`, owned by `root:rory-trader`

## Live Paper Data

The deployed dashboard reads from the VPS journal and latest Betfair snapshot files. Refresh those with an
explicit, one-shot paper session or the recurring timer:

```bash
sudo systemctl start rory-trader-paper-session
sudo systemctl status rory-trader-paper-session.timer
sudo journalctl -u rory-trader-paper-session -n 80 --no-pager
```

The command fetches current Betfair markets, saves snapshots, creates strategy proposals, simulates paper fills,
enforces stale/auth/exposure/loss controls, and appends to `/opt/rory-trader/runtime/journals/trading_journal.jsonl`.
The dashboard should then show fresh snapshot status, journal activity, any open paper positions, and the learning
review tables grouped by strategy, price bucket, and time-to-event.

Settle overdue paper positions with a dry run first:

```bash
sudo -u rory-trader bash -lc 'cd /opt/rory-trader && scripts/run-settlement-session.sh'
```

If the dry run shows expected Betfair `CLOSED` markets and runner statuses, apply a bounded batch:

```bash
sudo -u rory-trader bash -lc 'cd /opt/rory-trader && scripts/run-settlement-session.sh --apply --max-positions 500 --max-markets 50'
```

The apply path appends `resolution` events only. It calculates realized PnL from the paper fill, never places live
orders, and refuses live-enabled environments. A recurring settlement timer should call the same script and can be
disabled with:

```bash
sudo systemctl disable --now rory-trader-settlement.timer
sudo journalctl -u rory-trader-settlement -n 80 --no-pager
```

The dashboard's `Overdue settlement` count is the backlog of open paper positions old enough to be checked against
settled Betfair market books.

The dashboard API also exposes a token-protected operator trigger:

```bash
curl -sS -X POST \
  -H "X-Rory-Dashboard-Token: <token>" \
  -H "Content-Type: application/json" \
  -d '{"category":"tennis","max_results":100}' \
  https://api.your-domain.example/api/paper-session/run
```

This calls the same bounded paper-only script, refuses live-enabled environments, and returns parsed counts such as
`paper_fills_created`.

## Safety Checks

```bash
curl -i https://api.your-domain.example/api/health
curl -i -H "X-Rory-Dashboard-Token: <token>" https://api.your-domain.example/api/health
```

The first request should fail. The second should return health JSON with:

- `live_execution_available: false`
- `supports_live_execution: false`
- `live_enabled: false`

If the VPS is reachable by IP before DNS is attached, test the backend locally over SSH instead:

```bash
ssh root@46.62.217.82
TOKEN="$(sudo awk -F= '/^RORY_TRADER_DASHBOARD_TOKEN=/{print $2}' /opt/rory-trader/.env)"
curl -i -H "X-Rory-Dashboard-Token: $TOKEN" http://127.0.0.1:8000/api/health
```
