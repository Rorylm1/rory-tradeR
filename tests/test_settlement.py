from __future__ import annotations

from datetime import datetime, timedelta, timezone

from src.exchanges.common.models import (
    ExecutionReport,
    MarketSnapshot,
    PaperFill,
    SelectionSnapshot,
    StrategySignal,
)
from src.trading.accounting import journal_performance_summary
from src.trading.journal import JournalStore
from src.trading.settlement import settle_due_positions, settlement_due_positions


class FakeSettlementAdapter:
    def __init__(self, books):
        self.books = books
        self.calls = []

    def list_market_books(self, market_ids: list[str]) -> list[dict]:
        self.calls.append(market_ids)
        return [self.books[market_id] for market_id in market_ids if market_id in self.books]


def _snapshot(*, market_id: str = "1.100", selection_id: str = "42", event_start: datetime) -> MarketSnapshot:
    selection = SelectionSnapshot(
        exchange="betfair",
        market_id=market_id,
        selection_id=selection_id,
        market_title="Match Odds",
        selection_name="Selection",
        category="sports",
        subcategory="tennis",
        event_start=event_start,
        best_back=2.4,
        best_lay=2.48,
        last_traded=2.45,
        status="open",
        event_name="Player A v Player B",
        competition_name="Test Tennis",
        captured_at=event_start - timedelta(hours=4),
    )
    return MarketSnapshot(
        exchange="betfair",
        market_id=market_id,
        market_title="Match Odds",
        category="sports",
        subcategory="tennis",
        event_start=event_start,
        status="open",
        selections=[selection],
        event_name="Player A v Player B",
        competition_name="Test Tennis",
        captured_at=selection.captured_at,
    )


def _seed_position(
    journal_path,
    *,
    market_id: str = "1.100",
    selection_id: str = "42",
    event_start: datetime,
) -> str:
    store = JournalStore(journal_path)
    snapshot = _snapshot(market_id=market_id, selection_id=selection_id, event_start=event_start)
    signal = StrategySignal(
        strategy_name="betfair_tennis_pre_match_back_bucket",
        strategy_version="v1",
        market_id=market_id,
        selection_id=selection_id,
        side="back",
        confidence=0.8,
        reason="Eligible runner in target price bucket.",
        stake=2.0,
        requested_price=2.4,
        snapshot_timestamp=snapshot.captured_at,
        event_start=event_start,
        holding_period_hours=24.0,
        tags=["betfair", "sports", "tennis"],
    )
    proposal = store.record_proposal(signal, snapshot)
    assert proposal is not None
    store.record_execution(
        proposal.proposal_id,
        ExecutionReport(
            accepted=True,
            exchange="betfair",
            mode="paper",
            message="Paper fill created successfully.",
            fill=PaperFill(
                market_id=market_id,
                selection_id=selection_id,
                side="back",
                stake=2.0,
                fill_price=2.4,
                commission_paid=0.04,
                slippage_paid=0.01,
                timestamp=snapshot.captured_at + timedelta(seconds=1),
            ),
        ),
        mode="paper",
    )
    return proposal.proposal_id


def _closed_book(*, market_id: str = "1.100", selection_id: int = 42, runner_status: str = "WINNER") -> dict:
    return {
        "marketId": market_id,
        "status": "CLOSED",
        "runners": [
            {
                "selectionId": selection_id,
                "status": runner_status,
            }
        ],
    }


def test_settlement_due_positions_filters_old_open_betfair_positions(tmp_path):
    now = datetime(2026, 6, 28, 12, tzinfo=timezone.utc)
    journal_path = tmp_path / "journal.jsonl"
    due_id = _seed_position(journal_path, event_start=now - timedelta(hours=4))
    _seed_position(journal_path, market_id="1.101", event_start=now + timedelta(hours=2))

    summary = journal_performance_summary(journal_path)
    due = settlement_due_positions(summary, now=now, min_age_hours=3)

    assert due["proposal_id"].tolist() == [due_id]


def test_settle_due_positions_dry_run_does_not_write_resolution(tmp_path):
    now = datetime(2026, 6, 28, 12, tzinfo=timezone.utc)
    journal_path = tmp_path / "journal.jsonl"
    proposal_id = _seed_position(journal_path, event_start=now - timedelta(hours=4))
    adapter = FakeSettlementAdapter({"1.100": _closed_book()})

    report = settle_due_positions(adapter=adapter, journal_path=journal_path, dry_run=True, now=now)
    summary = journal_performance_summary(journal_path)

    assert adapter.calls == [["1.100"]]
    assert report["settleable_positions"] == 1
    assert report["settled_positions"] == 0
    assert report["candidates"][0]["proposal_id"] == proposal_id
    assert report["candidates"][0]["resolved_outcome"] == "won"
    assert len(summary["closed_positions"]) == 0


def test_settle_due_positions_apply_records_resolution_and_is_idempotent(tmp_path):
    now = datetime(2026, 6, 28, 12, tzinfo=timezone.utc)
    journal_path = tmp_path / "journal.jsonl"
    _seed_position(journal_path, event_start=now - timedelta(hours=4))
    adapter = FakeSettlementAdapter({"1.100": _closed_book(runner_status="LOSER")})

    first = settle_due_positions(adapter=adapter, journal_path=journal_path, dry_run=False, now=now)
    second = settle_due_positions(adapter=adapter, journal_path=journal_path, dry_run=False, now=now)
    summary = journal_performance_summary(journal_path)

    assert first["settled_positions"] == 1
    assert second["due_positions"] == 0
    assert len(summary["closed_positions"]) == 1
    closed = summary["closed_positions"].iloc[0]
    assert closed["resolved_outcome"] == "lost"
    assert closed["realized_pnl"] == -2.04


def test_settle_due_positions_skips_unclosed_market(tmp_path):
    now = datetime(2026, 6, 28, 12, tzinfo=timezone.utc)
    journal_path = tmp_path / "journal.jsonl"
    _seed_position(journal_path, event_start=now - timedelta(hours=4))
    adapter = FakeSettlementAdapter(
        {
            "1.100": {
                "marketId": "1.100",
                "status": "OPEN",
                "runners": [{"selectionId": 42, "status": "ACTIVE"}],
            }
        }
    )

    report = settle_due_positions(adapter=adapter, journal_path=journal_path, dry_run=False, now=now)

    assert report["settled_positions"] == 0
    assert report["skipped_reasons"] == {"market_not_closed": 1}
