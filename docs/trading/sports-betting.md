# Sports Betting Research Primer

This document is the entrypoint for Betfair sports-betting concepts used by `rory-tradeR`.

The repo is paper-only. Nothing here is evidence of an edge unless the paper journal proves it after commission,
slippage, stale-price checks, and realistic rejection reasons.

## Betfair Exchange Basics

Betfair is an exchange, not a fixed-odds bookmaker. Prices come from other exchange participants, and usable prices
depend on both odds and available size.

Decimal odds:
- `2.00` means a winning back bet returns stake plus the same amount in profit before commission.
- implied probability is approximately `1 / decimal_odds`.
- example: odds of `2.50` imply `40%` before fees and spread.

Back:
- backing is betting that a selection will win.
- for a paper back bet, maximum loss is the stake.
- paper realized PnL for a winning back position is `stake * (fill_price - 1) - commission`.
- paper realized PnL for a losing back position is `-stake - commission`.

Lay:
- laying is taking the other side of someone else's back bet.
- lay liability is roughly `stake * (odds - 1)`.
- first milestone strategy execution is back-only; lay math is documented for understanding spreads and future review.

## Liquidity And Spread

Liquidity is the available money at the top of the book. A price is not useful if the available size is too small for
the intended stake.

Spread is the gap between the best back and best lay prices. Wide spreads are a warning that:
- the displayed midpoint may not be executable,
- cash-out marks are noisy,
- a paper fill may look better than a real fill would have been,
- a strategy can be accidentally optimized to stale or thin prices.

Current paper controls reject thin top-of-book size and wide spreads before creating proposals.

## Commission, Slippage, And Marks

Commission reduces winning outcomes and should be visible in every paper fill. The default paper commission is `2%` of
stake.

Slippage is the price penalty applied to make paper fills less optimistic. The default is `25` basis points of decimal
odds.

Unrealized PnL is marked from the latest saved snapshot:
- for open back positions, the mark prefers latest best lay, then last traded, then best back.
- old or missing marks should not be treated as reliable.
- stale snapshots trigger dashboard guardrails.

## Stale Prices

Sports markets move quickly, especially near start time. A stale price can make a paper system look profitable while
being impossible to execute in reality.

Current stale-price controls:
- strategy evaluation rejects snapshots older than `RORY_TRADER_PAPER_MAX_SNAPSHOT_AGE_SECONDS`.
- the paper broker rejects stale or timestamp-missing snapshots.
- the dashboard shows snapshot age and stale status.

## Strategy Hypotheses

The current first strategy is deliberately simple:
- pre-match sports only,
- back-only,
- target mid-priced runners,
- require event start to be neither too soon nor too far away,
- require reasonable spread and available size,
- fixed small stake.

This is not a claimed edge. It is a journaled way to learn whether inherited price-bucket priors survive Betfair costs,
liquidity, timing, and rejection filters.

## Rejection Reasons

Rejections are research data. Common reason codes:
- `snapshot_stale`: snapshot too old for safe paper evaluation.
- `market_category_not_allowed`: market outside the current sports scope.
- `market_not_open`: market suspended, closed, or otherwise unavailable.
- `event_start_too_soon`: event is too close for the current pre-match hypothesis.
- `event_start_too_far`: event is too far away for the current holding-period hypothesis.
- `market_liquidity_too_low`: market total matched is below the configured threshold.
- `selection_not_open`: runner is not open.
- `missing_back_or_lay`: top-of-book prices are incomplete.
- `best_back_size_too_low`: available size at best back is below the configured threshold.
- `back_price_below_min` / `back_price_above_max`: runner is outside the target price bucket.
- `spread_too_wide`: best back to best lay gap is too large.

Dashboard rejection counts should be reviewed before judging a strategy. Zero fills can be a healthy outcome if the
system is correctly refusing unsafe markets.

## What Paper Results Teach

Useful paper results answer:
- did the strategy produce proposals only from fresh, liquid snapshots?
- were the fills small, bounded, and commission-adjusted?
- did open positions get marked from later snapshots?
- did manual resolutions produce realized PnL after commission?
- are rejection reasons dominated by a correct guardrail or by a strategy bug?
- does performance persist across replayed snapshots and later paper sessions?

Do not claim edge from:
- unmarked open positions,
- stale snapshots,
- tiny samples,
- ignored rejected trades,
- runs without commission and slippage,
- manual cherry-picking of settled outcomes.
