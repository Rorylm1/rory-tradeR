from datetime import datetime, timezone

from src.exchanges.common.models import MarketSnapshot, OrderIntent, SelectionSnapshot
from src.trading.paper_broker import BrokerConfig, PaperBroker


def _snapshot() -> MarketSnapshot:
    captured_at = datetime.now(timezone.utc)
    selection = SelectionSnapshot(
        exchange="betfair",
        market_id="1.100",
        selection_id="42",
        market_title="Example Market",
        selection_name="Selection",
        category="sports",
        subcategory="example",
        event_start=datetime.now(timezone.utc),
        best_back=2.5,
        best_lay=2.6,
        last_traded=2.55,
        status="open",
        captured_at=captured_at,
        best_back_size=100.0,
        best_lay_size=100.0,
    )
    return MarketSnapshot(
        exchange="betfair",
        market_id="1.100",
        market_title="Example Market",
        category="sports",
        subcategory="example",
        event_start=captured_at,
        status="open",
        selections=[selection],
        captured_at=captured_at,
    )


def test_paper_broker_creates_fill_for_paper_order():
    broker = PaperBroker(BrokerConfig(commission_rate=0.02, slippage_bps=10, max_stake_per_trade=100))
    intent = OrderIntent(
        exchange="betfair",
        market_id="1.100",
        selection_id="42",
        side="back",
        stake=25,
        requested_price=2.5,
        paper_only=True,
    )

    report = broker.execute(intent, _snapshot())

    assert report.accepted is True
    assert report.fill is not None
    assert report.fill.commission_paid == 0.5
    assert report.fill.fill_price > 2.5


def test_paper_broker_rejects_non_paper_intent():
    broker = PaperBroker()
    intent = OrderIntent(
        exchange="betfair",
        market_id="1.100",
        selection_id="42",
        side="back",
        stake=25,
        requested_price=2.5,
        paper_only=False,
    )

    report = broker.execute(intent, _snapshot())

    assert report.accepted is False


def test_paper_broker_rejects_stale_snapshot():
    snapshot = _snapshot()
    snapshot.captured_at = datetime(2020, 1, 1, tzinfo=timezone.utc)
    broker = PaperBroker(BrokerConfig(max_snapshot_age_seconds=60))
    intent = OrderIntent(
        exchange="betfair",
        market_id="1.100",
        selection_id="42",
        side="back",
        stake=25,
        requested_price=2.5,
        paper_only=True,
    )

    report = broker.execute(intent, snapshot)

    assert report.accepted is False
    assert "stale" in report.message
