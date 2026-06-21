from __future__ import annotations

from datetime import datetime, timedelta, timezone

from src.exchanges.common.models import MarketSnapshot, SelectionSnapshot
from src.trading.strategy import BackPriceBucketConfig, BackPriceBucketStrategy, strategy_for_category


def _snapshot(
    *,
    hours_to_event: float = 12,
    category: str = "sports",
    subcategory: str = "soccer",
    spread: float = 0.05,
    back: float = 2.4,
    captured_at: datetime | None = None,
    total_matched: float | None = 1000.0,
    best_back_size: float | None = 50.0,
):
    now = datetime.now(timezone.utc)
    captured_at = captured_at or now
    selection = SelectionSnapshot(
        exchange="betfair",
        market_id="1.100",
        selection_id="42",
        market_title="Example Market",
        selection_name="Selection",
        category=category,
        subcategory=subcategory,
        event_start=now + timedelta(hours=hours_to_event),
        best_back=back,
        best_lay=back + spread,
        last_traded=back,
        status="open",
        event_name="Arsenal v Chelsea",
        competition_name="Premier League",
        captured_at=captured_at,
        best_back_size=best_back_size,
    )
    return MarketSnapshot(
        exchange="betfair",
        market_id="1.100",
        market_title="Match Odds",
        category=category,
        subcategory=subcategory,
        event_start=selection.event_start,
        status="open",
        selections=[selection],
        event_name="Arsenal v Chelsea",
        competition_name="Premier League",
        captured_at=captured_at,
        total_matched=total_matched,
    )


def test_back_price_bucket_strategy_emits_signal_for_matching_snapshot():
    strategy = BackPriceBucketStrategy(BackPriceBucketConfig())

    signals = strategy.evaluate([_snapshot()])

    assert len(signals) == 1
    signal = signals[0]
    assert signal.strategy_name == "betfair_pre_match_back_bucket"
    assert signal.side == "back"
    assert signal.requested_price == 2.4


def test_back_price_bucket_strategy_skips_events_that_start_too_soon():
    strategy = BackPriceBucketStrategy(BackPriceBucketConfig(min_hours_to_event=6))

    signals = strategy.evaluate([_snapshot(hours_to_event=1)])

    assert signals == []


def test_back_price_bucket_strategy_skips_non_sports_snapshots():
    strategy = BackPriceBucketStrategy(BackPriceBucketConfig())

    signals = strategy.evaluate([_snapshot(category="politics")])

    assert signals == []


def test_back_price_bucket_strategy_skips_wide_spreads():
    strategy = BackPriceBucketStrategy(BackPriceBucketConfig(max_spread=0.08))

    signals = strategy.evaluate([_snapshot(spread=0.25)])

    assert signals == []


def test_back_price_bucket_strategy_records_rejection_reasons():
    strategy = BackPriceBucketStrategy(BackPriceBucketConfig(max_spread=0.08))

    decisions = strategy.evaluate_decisions([_snapshot(spread=0.25)])

    assert len(decisions) == 1
    assert decisions[0].accepted is False
    assert decisions[0].reason_code == "spread_too_wide"


def test_back_price_bucket_strategy_converts_accepted_decisions_to_signals():
    strategy = BackPriceBucketStrategy(BackPriceBucketConfig())

    decisions = strategy.evaluate_decisions([_snapshot()])
    signals = strategy.signals_from_decisions(decisions)

    assert len(decisions) == 1
    assert decisions[0].accepted is True
    assert len(signals) == 1
    assert signals[0].selection_id == "42"


def test_back_price_bucket_strategy_rejects_stale_snapshots():
    strategy = BackPriceBucketStrategy(BackPriceBucketConfig(max_snapshot_age_seconds=60))
    stale_time = datetime(2020, 1, 1, tzinfo=timezone.utc)

    decisions = strategy.evaluate_decisions([_snapshot(captured_at=stale_time)])

    assert decisions[0].accepted is False
    assert decisions[0].reason_code == "snapshot_stale"


def test_back_price_bucket_strategy_rejects_thin_markets():
    strategy = BackPriceBucketStrategy(BackPriceBucketConfig(min_market_total_matched=100))

    decisions = strategy.evaluate_decisions([_snapshot(total_matched=10)])

    assert decisions[0].accepted is False
    assert decisions[0].reason_code == "market_liquidity_too_low"


def test_back_price_bucket_strategy_rejects_small_available_back_size():
    strategy = BackPriceBucketStrategy(BackPriceBucketConfig(min_best_back_size=10))

    decisions = strategy.evaluate_decisions([_snapshot(best_back_size=2)])

    assert decisions[0].accepted is False
    assert decisions[0].reason_code == "best_back_size_too_low"


def test_strategy_for_category_uses_tennis_specific_strategy():
    strategy = strategy_for_category("tennis")

    signals = strategy.evaluate([_snapshot(subcategory="tennis")])

    assert len(signals) == 1
    assert signals[0].strategy_name == "betfair_tennis_pre_match_back_bucket"
    assert "tennis" in signals[0].tags


def test_tennis_strategy_rejects_non_tennis_sports():
    strategy = strategy_for_category("tennis")

    decisions = strategy.evaluate_decisions([_snapshot(subcategory="soccer")])

    assert decisions[0].accepted is False
    assert decisions[0].reason_code == "subcategory_not_allowed"


def test_tennis_strategy_allows_nearer_scouting_window_by_default():
    strategy = strategy_for_category("tennis")

    accepted = strategy.evaluate_decisions([_snapshot(subcategory="tennis", hours_to_event=0.75)])
    rejected = strategy.evaluate_decisions([_snapshot(subcategory="tennis", hours_to_event=0.25)])

    assert accepted[0].accepted is True
    assert rejected[0].accepted is False
    assert rejected[0].reason_code == "event_start_too_soon"


def test_tennis_strategy_window_is_configurable(monkeypatch):
    monkeypatch.setenv("RORY_TRADER_TENNIS_MIN_HOURS_TO_EVENT", "2")
    strategy = strategy_for_category("tennis")

    decisions = strategy.evaluate_decisions([_snapshot(subcategory="tennis", hours_to_event=1)])

    assert decisions[0].accepted is False
    assert decisions[0].reason_code == "event_start_too_soon"
