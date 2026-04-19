# Exchange Integration Notes

## Objective

Add safe, normalized exchange access for Betfair and Smarkets without enabling live order placement in milestone one.

## Capability Matrix

| Capability | Betfair | Smarkets |
|---|---|---|
| Credential validation | Planned in milestone one | Planned in milestone one |
| Approval status reporting | N/A | Yes |
| Market discovery | Planned in milestone one | Planned in milestone one |
| Price polling | Planned in milestone one | Planned in milestone one where API access exists |
| Normalized market snapshots | Planned in milestone one | Planned in milestone one |
| Live order placement | Disabled | Disabled |

## Betfair

### Setup expectations

- valid Betfair account
- app access / application key
- username and password
- client certificate and key for non-interactive login

### First-pass target

- config validation
- non-interactive session establishment when credentials are complete
- market discovery
- market book retrieval
- normalized odds and selection mapping

## Smarkets

### Setup expectations

- active and verified Smarkets account
- approved API access
- token/approval info configured in local env

### First-pass target

- readiness and approval-state reporting
- API-aware market discovery scaffolding
- normalized market mapping

### Limitation

Smarkets integration should fail clearly when approval or token access is missing instead of pretending the exchange is ready.
