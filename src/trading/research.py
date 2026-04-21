from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd

from src.common.paths import get_data_root


def inherited_market_priors(data_root: Path | None = None) -> pd.DataFrame:
    root = Path(data_root) if data_root is not None else get_data_root()
    trades_dir = root / "kalshi" / "trades"
    markets_dir = root / "kalshi" / "markets"

    if not trades_dir.exists() or not markets_dir.exists():
        return pd.DataFrame()

    con = duckdb.connect()
    return con.execute(
        f"""
        WITH resolved_markets AS (
            SELECT ticker, result
            FROM '{markets_dir}/*.parquet'
            WHERE status = 'finalized'
              AND result IN ('yes', 'no')
        ),
        all_positions AS (
            SELECT
                CASE WHEN t.taker_side = 'yes' THEN t.yes_price ELSE t.no_price END AS price_cents,
                CASE WHEN t.taker_side = m.result THEN 1 ELSE 0 END AS won
            FROM '{trades_dir}/*.parquet' t
            INNER JOIN resolved_markets m ON t.ticker = m.ticker

            UNION ALL

            SELECT
                CASE WHEN t.taker_side = 'yes' THEN t.no_price ELSE t.yes_price END AS price_cents,
                CASE WHEN t.taker_side != m.result THEN 1 ELSE 0 END AS won
            FROM '{trades_dir}/*.parquet' t
            INNER JOIN resolved_markets m ON t.ticker = m.ticker
        ),
        bucketed AS (
            SELECT
                FLOOR(price_cents / 5.0) * 5 AS price_bucket_start,
                price_cents,
                won
            FROM all_positions
            WHERE price_cents BETWEEN 1 AND 99
        )
        SELECT
            price_bucket_start,
            price_bucket_start + 5 AS price_bucket_end,
            COUNT(*) AS trades,
            AVG(price_cents / 100.0) AS avg_implied_probability,
            AVG(won) AS actual_win_rate,
            AVG(won) - AVG(price_cents / 100.0) AS calibration_gap
        FROM bucketed
        GROUP BY price_bucket_start
        HAVING COUNT(*) >= 100
        ORDER BY price_bucket_start
        """
    ).df()
