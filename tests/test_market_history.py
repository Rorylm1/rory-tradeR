from datetime import datetime, timezone

import pandas as pd

from src.exchanges.common.models import MarketSnapshot, SelectionSnapshot
from src.trading.market_history import save_market_snapshots


def test_save_market_snapshots_writes_flattened_parquet(tmp_path):
    captured_at = datetime.now(timezone.utc)
    selection = SelectionSnapshot(
        exchange="betfair",
        market_id="1.100",
        selection_id="42",
        market_title="Match Odds",
        selection_name="Selection",
        category="sports",
        subcategory="soccer",
        event_start=captured_at,
        best_back=2.4,
        best_lay=2.5,
        last_traded=2.45,
        status="open",
        event_name="Arsenal v Chelsea",
        competition_name="Premier League",
        captured_at=captured_at,
        best_back_size=120.0,
        best_lay_size=90.0,
        traded_volume=2500.0,
        total_matched=5000.0,
    )
    snapshot = MarketSnapshot(
        exchange="betfair",
        market_id="1.100",
        market_title="Match Odds",
        category="sports",
        subcategory="soccer",
        event_start=captured_at,
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

    path = save_market_snapshots([snapshot], output_dir=tmp_path, captured_at=captured_at)

    assert path is not None
    df = pd.read_parquet(path)
    assert df.loc[0, "competition_name"] == "Premier League"
    assert df.loc[0, "selection_name"] == "Selection"
    assert df.loc[0, "best_back_size"] == 120.0
    assert df.loc[0, "market_total_matched"] == 5000.0
    assert df.loc[0, "in_play"] == False  # noqa: E712
