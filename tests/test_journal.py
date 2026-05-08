from datetime import datetime, timedelta, timezone

import pytest

from src.exchanges.common.models import ExecutionReport, MarketSnapshot, PaperFill, SelectionSnapshot, StrategySignal
from src.trading.accounting import resolve_journal_position
from src.trading.journal import JournalStore, journal_performance_summary
from src.trading.market_history import save_market_snapshots
from src.trading.strategy import BackPriceBucketConfig, BackPriceBucketStrategy


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


def test_journal_store_records_strategy_evaluation_decisions(tmp_path):
    store = JournalStore(tmp_path / "journal.jsonl")
    strategy = BackPriceBucketStrategy(BackPriceBucketConfig(max_spread=0.04))
    decisions = strategy.evaluate_decisions([_snapshot()])

    store.record_strategy_evaluation(strategy.definition, decisions, snapshots_seen=1)
    events = store.load_events()

    assert len(events) == 1
    payload = events[0]["payload"]
    assert events[0]["event_type"] == "strategy_evaluation"
    assert payload["snapshots_seen"] == 1
    assert payload["accepted_count"] == 0
    assert payload["rejected_count"] == 1
    assert payload["rejection_counts"]["spread_too_wide"] == 1
    assert payload["decisions"][0]["reason_code"] == "spread_too_wide"


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

    assert not summary["overview"].empty
    assert int(summary["overview"].iloc[0]["executed_positions"]) == 1
    assert not summary["strategy"].empty
    assert int(summary["strategy"].iloc[0]["executed_positions"]) == 1
    assert int(summary["strategy"].iloc[0]["open_positions"]) == 1
    assert not summary["price_bucket"].empty


def test_journal_summary_marks_open_positions_with_latest_snapshot(tmp_path):
    journal_path = tmp_path / "journal.jsonl"
    snapshot_dir = tmp_path / "snapshots"
    store = JournalStore(journal_path)
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
            fill_price=2.40,
            commission_paid=0.04,
            slippage_paid=0.01,
            timestamp=datetime.now(timezone.utc),
        ),
    )
    store.record_execution(proposal.proposal_id, report, mode="paper")

    later_snapshot = _snapshot()
    later_snapshot.captured_at = snapshot.captured_at + timedelta(hours=1)
    later_snapshot.selections[0].captured_at = later_snapshot.captured_at
    later_snapshot.selections[0].best_back = 2.15
    later_snapshot.selections[0].best_lay = 2.20
    later_snapshot.selections[0].last_traded = 2.18
    save_market_snapshots([later_snapshot], output_dir=snapshot_dir, captured_at=later_snapshot.captured_at)

    summary = journal_performance_summary(journal_path, snapshot_dir=snapshot_dir)

    assert len(summary["open_positions"]) == 1
    open_position = summary["open_positions"].iloc[0]
    assert open_position["mark_source"] == "best_lay"
    assert open_position["unrealized_pnl"] == pytest.approx(0.1418)


def test_resolve_journal_position_records_realized_pnl(tmp_path):
    journal_path = tmp_path / "journal.jsonl"
    store = JournalStore(journal_path)
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
            fill_price=2.40,
            commission_paid=0.04,
            slippage_paid=0.01,
            timestamp=datetime.now(timezone.utc),
        ),
    )
    store.record_execution(proposal.proposal_id, report, mode="paper")

    resolution = resolve_journal_position(proposal.proposal_id, "won", path=journal_path, note="Manual settle")
    summary = journal_performance_summary(journal_path)

    assert resolution["realized_pnl"] == pytest.approx(2.76)
    assert len(summary["closed_positions"]) == 1
    assert summary["closed_positions"].iloc[0]["resolved_outcome"] == "won"
    assert summary["closed_positions"].iloc[0]["realized_pnl"] == pytest.approx(2.76)


def test_resolve_journal_position_rejects_double_resolution(tmp_path):
    journal_path = tmp_path / "journal.jsonl"
    store = JournalStore(journal_path)
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
            fill_price=2.40,
            commission_paid=0.04,
            slippage_paid=0.01,
            timestamp=datetime.now(timezone.utc),
        ),
    )
    store.record_execution(proposal.proposal_id, report, mode="paper")
    resolve_journal_position(proposal.proposal_id, "lost", path=journal_path)

    with pytest.raises(ValueError, match="already resolved"):
        resolve_journal_position(proposal.proposal_id, "won", path=journal_path)
