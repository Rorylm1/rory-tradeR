# Exchange Integration Notes

## Objective

Add safe, normalized exchange access for Betfair and Smarkets without enabling live order placement in milestone one.

## Capability Matrix

| Capability | Betfair | Smarkets |
|---|---|---|
| Credential validation | Implemented | Implemented |
| Approval status reporting | N/A | Yes (approval_required / missing_token / ready) |
| Market normalization | Implemented | Implemented |
| Category inference | Implemented (event type ID) | Implemented (event slug) |
| Price polling | Implemented for `list_markets` snapshots | Stubbed (returns empty) |
| Live order placement | Disabled | Disabled |

## Validation Status Codes

### Betfair

| Status | Meaning |
|---|---|
| `ready` | Credentials valid, login successful |
| `missing_credentials` | One or more env vars not set |
| `missing_cert_files` | Cert or key file not found on disk |
| `login_failed` | Credentials rejected by Betfair |

### Smarkets

| Status | Meaning |
|---|---|
| `ready` | Token present and API enabled |
| `approval_required` | SMARKETS_API_ENABLED is not "true" |
| `missing_token` | SMARKETS_API_TOKEN not set |

## Normalized Market Model

Both exchanges normalize to the same `MarketSnapshot` / `SelectionSnapshot` structure:

```
exchange         # "betfair" or "smarkets"
market_id        # Exchange-native market identifier
selection_id     # Exchange-native selection/contract ID
market_title     # Human-readable market name
selection_name   # Human-readable selection name
category         # Inferred category (sports, politics, etc.)
subcategory      # Inferred subcategory (soccer, tennis, etc.)
event_start      # UTC datetime of event start
best_back        # Best available back price (decimal odds)
best_lay         # Best available lay price (decimal odds)
last_traded      # Last traded price (decimal odds)
status           # Normalized status (open, suspended, closed)
raw_payload      # Original API response preserved for debugging
```

## Category Inference

### Betfair

Categories are inferred from the `eventType.id` field:

| Event Type ID | Category | Subcategory |
|---|---|---|
| 1 | sports | soccer |
| 2 | sports | tennis |
| 7 | sports | horse_racing |
| 7524 | sports | american_football |
| 2378961 | politics | politics |
| (unknown) | unknown | unknown |

### Smarkets

Categories are inferred from the event `full_slug` prefix:

| Slug Prefix | Category | Subcategory |
|---|---|---|
| football/ | sports | soccer |
| tennis/ | sports | tennis |
| horse-racing/ | sports | horse_racing |
| politics/ | politics | politics |
| (unknown) | unknown | unknown |

## Betfair

### Setup Requirements

- Valid Betfair account
- App access / application key
- Username and password
- Client certificate and key for non-interactive login

### Environment Variables

```
BETFAIR_USERNAME=<username>
BETFAIR_PASSWORD=<password>
BETFAIR_APP_KEY=<application key>
BETFAIR_CERT_FILE=<path to .crt file>
BETFAIR_KEY_FILE=<path to .key file>
```

### Implementation Status

- [x] Credential validation with cert-based login
- [x] Market normalization (`normalize_market` static method)
- [x] Category inference from event type
- [x] Market discovery (`list_markets`)
- [x] Price polling for sampled market snapshots

## Smarkets

### Setup Requirements

- Active and verified Smarkets account
- Approved API access
- Token configured in local env

### Environment Variables

```
SMARKETS_API_TOKEN=<api token>
SMARKETS_API_ENABLED=true  # Set only after approval confirmed
SMARKETS_API_BASE_URL=https://api.smarkets.com  # Optional override
```

### Implementation Status

- [x] Approval status reporting (distinguishes disabled/missing/ready)
- [x] Market normalization (`normalize_market` static method)
- [x] Category inference from event slug
- [x] Price conversion from basis points to decimal odds
- [ ] Market discovery (`list_markets` returns empty)
- [ ] Price polling

### Notes

- Smarkets prices are in basis points (0-10000), converted to decimal odds
- Integration fails clearly when approval or token is missing
