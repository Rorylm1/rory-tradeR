from datetime import datetime, timedelta, timezone

from src.exchanges.common.models import MarketSnapshot, SelectionSnapshot
from src.trading.strategy import BackPriceBucketConfig, BackPriceBucketStrategy


def _snapshot(*, hours_to_event: float = 12, category: str = "sports", spread: float = 0.05, back: float = 2.4):
    now = datetime.now(timezone.utc)
    selection = SelectionSnapshot(
        exchange="betfair",
        market_id="1.100",
        selection_id="42",
        market_title="Example Market",
        selection_name="Selection",
        category=category,
        subcategory="soccer",
        event_start=now + timedelta(hours=hours_to_event),
        best_back=back,
        best_lay=back + spread,
        last_traded=back,
        status="open",
        event_name="Arsenal v Chelsea",
        competition_name="Premier League",
    )
    return MarketSnapshot(
        exchange="betfair",
        market_id="1.100",
        market_title="Match Odds",
        category=category,
        subcategory="soccer",
        event_start=selection.event_start,
        status="open",
        selections=[selection],
        event_name="Arsenal v Chelsea",
        competition_name="Premier League",
        captured_at=now,
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
