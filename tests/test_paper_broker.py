from datetime import datetime, timezone

from src.exchanges.common.models import (
    ExecutionReport,
    MarketSnapshot,
    OrderIntent,
    PaperFill,
    SelectionSnapshot,
    StrategySignal,
)
from src.trading.accounting import resolve_journal_position
from src.trading.journal import JournalStore
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


def _signal(snapshot: MarketSnapshot, *, stake: float = 2.0) -> StrategySignal:
    return StrategySignal(
        strategy_name="test_strategy",
        strategy_version="v1",
        market_id=snapshot.market_id,
        selection_id="42",
        side="back",
        confidence=0.8,
        reason="Test signal.",
        stake=stake,
        requested_price=2.5,
        snapshot_timestamp=snapshot.captured_at,
        event_start=snapshot.event_start,
        holding_period_hours=24.0,
        tags=["test"],
    )


def _intent(*, stake: float = 25) -> OrderIntent:
    return OrderIntent(
        exchange="betfair",
        market_id="1.100",
        selection_id="42",
        side="back",
        stake=stake,
        requested_price=2.5,
        paper_only=True,
    )


def test_paper_broker_creates_fill_for_paper_order():
    broker = PaperBroker(
        BrokerConfig(
            commission_rate=0.02,
            slippage_bps=10,
            max_stake_per_trade=100,
            max_market_exposure=100,
            max_daily_loss=100,
        )
    )

    report = broker.execute(_intent(), _snapshot())

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


def test_paper_broker_rejects_when_market_exposure_would_exceed_limit(tmp_path):
    journal_path = tmp_path / "journal.jsonl"
    store = JournalStore(journal_path)
    snapshot = _snapshot()
    proposal = store.record_proposal(_signal(snapshot, stake=5.0), snapshot)
    assert proposal is not None
    store.record_execution(
        proposal.proposal_id,
        ExecutionReport(
            accepted=True,
            exchange="betfair",
            mode="paper",
            message="Paper fill created successfully.",
            fill=PaperFill(
                market_id="1.100",
                selection_id="42",
                side="back",
                stake=5.0,
                fill_price=2.5,
                commission_paid=0.1,
                slippage_paid=0.0,
                timestamp=datetime.now(timezone.utc),
            ),
        ),
        mode="paper",
    )
    broker = PaperBroker(
        BrokerConfig(max_stake_per_trade=100, max_market_exposure=6.0, max_daily_loss=100),
        journal_path=journal_path,
    )

    report = broker.execute(_intent(stake=2.0), snapshot)

    assert report.accepted is False
    assert "max_market_exposure" in report.message


def test_paper_broker_rejects_after_daily_loss_limit_is_reached(tmp_path):
    journal_path = tmp_path / "journal.jsonl"
    store = JournalStore(journal_path)
    snapshot = _snapshot()
    proposal = store.record_proposal(_signal(snapshot, stake=5.0), snapshot)
    assert proposal is not None
    store.record_execution(
        proposal.proposal_id,
        ExecutionReport(
            accepted=True,
            exchange="betfair",
            mode="paper",
            message="Paper fill created successfully.",
            fill=PaperFill(
                market_id="1.100",
                selection_id="42",
                side="back",
                stake=5.0,
                fill_price=2.5,
                commission_paid=0.1,
                slippage_paid=0.0,
                timestamp=datetime.now(timezone.utc),
            ),
        ),
        mode="paper",
    )
    resolve_journal_position(proposal.proposal_id, "lost", path=journal_path)
    broker = PaperBroker(
        BrokerConfig(max_stake_per_trade=100, max_market_exposure=100, max_daily_loss=5.0),
        journal_path=journal_path,
    )

    report = broker.execute(_intent(stake=1.0), snapshot)

    assert report.accepted is False
    assert "max_daily_loss" in report.message
