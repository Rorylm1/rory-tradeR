# Milestone 04 To-Do

## Objective

Build the paper-trading engine, inherited-priors research loop, and append-only execution journal.

## Checklist

- [x] Define `Strategy`, `PaperBroker`, and portfolio-state contracts.
- [x] Implement paper fill simulation against normalized prices.
- [x] Implement commission and slippage models.
- [x] Implement open-position and closed-position accounting.
- [x] Implement realized and unrealized PnL tracking.
- [x] Implement max stake, max exposure, and max daily loss controls.
- [x] Implement stale-data and auth-failure kill switches.
- [x] Implement append-only execution journaling.
- [x] Add a `paper` command for simulated sessions.
- [x] Add an inherited-priors report using Jon Becker's data as a research template.
- [x] Add a journal-report command for reviewing our own proposals and fills.
- [x] Add a `replay` command for deterministic playback from saved snapshots.
- [x] Add tests for PnL reconciliation, journal output, and safety controls.
  - PnL reconciliation and journal output coverage added.
  - Stale snapshot and thin-liquidity safety coverage added.
  - Max exposure and max daily loss safety coverage added.

## Exit Criteria

- [x] Paper sessions can run without any live exchange execution.
- [x] Journal output is deterministic and reviewable.
- [x] Risk controls fail closed rather than continuing in an unsafe state.
