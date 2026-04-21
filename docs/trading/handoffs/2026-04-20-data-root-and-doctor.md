# Handoff - 2026-04-20

## Summary

Today we wired the repo to use the verified selective dataset without copying it into the live `data/` directory.

The code now supports a shared data-root helper with this precedence:

1. `RORY_TRADER_DATA_ROOT` if explicitly set
2. `runtime/quarantine/extracted-lite/data` if it contains the only real local dataset
3. repo-local `data/`

## Files Added

- `src/common/paths.py`
- `tests/test_data_paths.py`

## Files Updated

- `src/common/storage.py`
- `src/common/util/package.py`
- `src/indexers/kalshi/markets.py`
- `src/indexers/kalshi/trades.py`
- `src/indexers/polymarket/blocks.py`
- `src/indexers/polymarket/fpmm_trades.py`
- `src/indexers/polymarket/markets.py`
- `src/indexers/polymarket/trades.py`
- `main.py`
- `.env.example`
- `docs/trading/security.md`

## Result

`uv run main.py doctor` now reports the active data root and exchange readiness without exposing secrets:

- active data root: `runtime/quarantine/extracted-lite/data`
- data root exists: `yes`
- Betfair status: ready when valid local credentials are present
- Smarkets status: disabled until approval is confirmed

## Validation

Focused tests passed:
- `tests/test_data_paths.py`
- `tests/test_data_verify.py`
- `tests/test_doctor.py`
- `tests/test_paper_broker.py`
- `tests/test_backfill_cursor.py`

Result:
- `9 passed`

## Notes

- A Python 3.9 compatibility issue in `src/common/util/package.py` was fixed while wiring the data-root support.
- There are still parallel uncommitted exchange/doc changes in the repo from other work. They were preserved.

## Recommended Next Step

Now that the dataset path is stable, the clean next move is:

1. make the repo explicitly Betfair-first in planning/docs
2. turn the `markets` command from a placeholder into real Betfair normalized output
3. keep Smarkets as optional/later unless access is confirmed
