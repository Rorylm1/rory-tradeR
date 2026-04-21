from datetime import datetime, timedelta, timezone

from src.exchanges.common.models import ExecutionReport, MarketSnapshot, PaperFill, SelectionSnapshot, StrategySignal
from src.trading.journal import JournalStore, journal_performance_summary


def _snapshot() -> MarketSnapshot:
    now = datetime.now(timezone.utc)
    selection = SelectionSnapshot(
        exchange="betfair",
        market_id="1.100",
        selection_id="42",
        market_title="Match Odds",
        selection_name="Selection",
        category="sports",
        subcategory="soccer",
        event_start=now + timedelta(hours=12),
        best_back=2.4,
        best_lay=2.48,
        last_traded=2.45,
        status="open",
        event_name="Arsenal v Chelsea",
        competition_name="Premier League",
        captured_at=now,
    )
    return MarketSnapshot(
        exchange="betfair",
        market_id="1.100",
        market_title="Match Odds",
        category="sports",
        subcategory="soccer",
        event_start=selection.event_start,
        status="open",
        selections=[selection],
        event_name="Arsenal v Chelsea",
        competition_name="Premier League",
        captured_at=now,
    )


def _signal(snapshot: MarketSnapshot) -> StrategySignal:
    return StrategySignal(
        strategy_name="betfair_pre_match_back_bucket",
        strategy_version="v1",
        market_id=snapshot.market_id,
        selection_id="42",
        side="back",
        confidence=0.8,
        reason="Eligible runner in target price bucket.",
        stake=2.0,
        requested_price=2.4,
        snapshot_timestamp=snapshot.captured_at,
        event_start=snapshot.event_start,
        holding_period_hours=24.0,
        tags=["betfair", "sports"],
    )


def test_journal_store_suppresses_duplicate_proposals(tmp_path):
    store = JournalStore(tmp_path / "journal.jsonl")
    snapshot = _snapshot()
    signal = _signal(snapshot)

    proposal1 = store.record_proposal(signal, snapshot)
    proposal2 = store.record_proposal(signal, snapshot)

    assert proposal1 is not None
    assert proposal2 is None


def test_journal_summary_includes_strategy_and_bucket_metrics(tmp_path):
    store = JournalStore(tmp_path / "journal.jsonl")
    snapshot = _snapshot()
    signal = _signal(snapshot)
    proposal = store.record_proposal(signal, snapshot)
    assert proposal is not None

    report = ExecutionReport(
        accepted=True,
        exchange="betfair",
        mode="paper",
        message="Paper fill created successfully.",
        fill=PaperFill(
            market_id="1.100",
            selection_id="42",
            side="back",
            stake=2.0,
            fill_price=2.41,
            commission_paid=0.04,
            slippage_paid=0.01,
            timestamp=datetime.now(timezone.utc),
        ),
    )
    store.record_execution(proposal.proposal_id, report, mode="paper")

    summary = journal_performance_summary(tmp_path / "journal.jsonl")

    assert not summary["strategy"].empty
    assert int(summary["strategy"].iloc[0]["proposals"]) == 1
    assert int(summary["strategy"].iloc[0]["accepted_trades"]) == 1
    assert not summary["price_bucket"].empty
