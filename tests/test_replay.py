from datetime import datetime, timedelta, timezone

from main import replay
from src.exchanges.common.models import MarketSnapshot, SelectionSnapshot
from src.trading.journal import JournalStore
from src.trading.market_history import save_market_snapshots


def _snapshot() -> MarketSnapshot:
    captured_at = datetime.now(timezone.utc).replace(microsecond=0)
    event_start = captured_at + timedelta(hours=12)
    selection = SelectionSnapshot(
        exchange="betfair",
        market_id="1.100",
        selection_id="42",
        market_title="Match Odds",
        selection_name="Selection",
        category="sports",
        subcategory="soccer",
        event_start=event_start,
        best_back=2.4,
        best_lay=2.46,
        last_traded=2.42,
        status="open",
        event_name="Arsenal v Chelsea",
        competition_name="Premier League",
        captured_at=captured_at,
        best_back_size=120.0,
        best_lay_size=100.0,
        traded_volume=2500.0,
        total_matched=5000.0,
    )
    return MarketSnapshot(
        exchange="betfair",
        market_id="1.100",
        market_title="Match Odds",
        category="sports",
        subcategory="soccer",
        event_start=event_start,
        status="open",
        selections=[selection],
        event_name="Arsenal v Chelsea",
        competition_name="Premier League",
        captured_at=captured_at,
        total_matched=5000.0,
        total_available=1000.0,
        in_play=False,
        is_market_data_delayed=False,
    )


def test_replay_writes_deterministic_paper_journal(tmp_path):
    snapshot_path = save_market_snapshots([_snapshot()], output_dir=tmp_path / "snapshots")
    assert snapshot_path is not None
    output_one = tmp_path / "replay-one.jsonl"
    output_two = tmp_path / "replay-two.jsonl"

    replay(str(snapshot_path), str(output_one))
    replay(str(snapshot_path), str(output_two))

    assert output_one.read_text() == output_two.read_text()
    events = JournalStore(output_one).load_events()
    assert [event["event_type"] for event in events] == [
        "snapshot_collection",
        "strategy_evaluation",
        "proposal",
        "execution",
    ]
    assert events[-1]["payload"]["accepted"] is True
