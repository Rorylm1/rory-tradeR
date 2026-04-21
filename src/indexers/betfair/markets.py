from __future__ import annotations

import os
from datetime import datetime, timezone

from src.common.indexer import Indexer
from src.exchanges import BetfairAdapter
from src.trading.market_history import save_market_snapshots


class BetfairMarketsIndexer(Indexer):
    def __init__(self):
        super().__init__(
            name="betfair_markets",
            description="Collect normalized Betfair market snapshots for later paper-trading and research.",
        )

    def run(self) -> None:
        category = os.getenv("BETFAIR_MARKETS_CATEGORY", "sports")
        max_results = int(os.getenv("BETFAIR_MARKETS_MAX_RESULTS", "25"))

        adapter = BetfairAdapter()
        validation = adapter.validate_credentials()
        if not validation.ok:
            raise RuntimeError(f"Betfair markets indexer cannot run: {validation.message}")

        captured_at = datetime.now(timezone.utc)
        snapshots = adapter.list_markets(category=category, max_results=max_results)
        for snapshot in snapshots:
            snapshot.captured_at = captured_at

        path = save_market_snapshots(snapshots, captured_at=captured_at)
        print(
            f"Saved {len(snapshots)} Betfair market snapshots "
            f"for category={category} max_results={max_results} to {path}"
        )
