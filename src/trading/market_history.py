from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from src.common.paths import data_path
from src.exchanges.common.models import MarketSnapshot


def snapshot_history_dir(output_dir: Path | None = None) -> Path:
    return Path(output_dir) if output_dir is not None else data_path("betfair", "snapshots")


def latest_snapshot_path(output_dir: Path | None = None) -> Path | None:
    snapshot_dir = snapshot_history_dir(output_dir)
    if not snapshot_dir.exists():
        return None

    paths = sorted(snapshot_dir.glob("snapshots_*.parquet"))
    if not paths:
        return None
    return paths[-1]


def flatten_market_snapshots(
    snapshots: list[MarketSnapshot],
    captured_at: datetime | None = None,
) -> list[dict]:
    rows: list[dict] = []
    captured_at = captured_at or datetime.now(timezone.utc)

    for snapshot in snapshots:
        snapshot_time = snapshot.captured_at or captured_at
        for selection in snapshot.selections:
            rows.append(
                {
                    "captured_at": snapshot_time,
                    "exchange": snapshot.exchange,
                    "market_id": snapshot.market_id,
                    "market_title": snapshot.market_title,
                    "selection_id": selection.selection_id,
                    "selection_name": selection.selection_name,
                    "category": selection.category,
                    "subcategory": selection.subcategory,
                    "event_start": selection.event_start,
                    "event_name": selection.event_name or snapshot.event_name,
                    "competition_name": selection.competition_name or snapshot.competition_name,
                    "status": selection.status,
                    "best_back": selection.best_back,
                    "best_lay": selection.best_lay,
                    "last_traded": selection.last_traded,
                    "implied_probability": selection.implied_probability,
                }
            )
    return rows


def save_market_snapshots(
    snapshots: list[MarketSnapshot],
    output_dir: Path | None = None,
    captured_at: datetime | None = None,
) -> Path | None:
    if not snapshots:
        return None

    rows = flatten_market_snapshots(snapshots, captured_at=captured_at)
    if not rows:
        return None

    snapshot_dir = snapshot_history_dir(output_dir)
    snapshot_dir.mkdir(parents=True, exist_ok=True)

    timestamp = (captured_at or datetime.now(timezone.utc)).strftime("%Y%m%dT%H%M%SZ")
    path = snapshot_dir / f"snapshots_{timestamp}.parquet"
    pd.DataFrame(rows).to_parquet(path, index=False)
    return path


def latest_snapshot_marks(snapshot_dir: Path | None = None) -> pd.DataFrame:
    path = latest_snapshot_path(snapshot_dir)
    if path is None:
        return pd.DataFrame()

    df = pd.read_parquet(path)
    if df.empty:
        return df

    if "captured_at" in df.columns:
        df["captured_at"] = pd.to_datetime(df["captured_at"], utc=True, errors="coerce")

    marks = df.sort_values("captured_at").drop_duplicates(["market_id", "selection_id"], keep="last").copy()
    marks["mark_price"] = marks["best_lay"].combine_first(marks["last_traded"]).combine_first(marks["best_back"])
    marks["mark_source"] = pd.Series(pd.NA, index=marks.index, dtype="object")
    marks.loc[marks["best_lay"].notna(), "mark_source"] = "best_lay"
    marks.loc[marks["best_lay"].isna() & marks["last_traded"].notna(), "mark_source"] = "last_traded"
    marks.loc[marks["best_lay"].isna() & marks["last_traded"].isna() & marks["best_back"].notna(), "mark_source"] = (
        "best_back"
    )
    return marks.rename(columns={"captured_at": "mark_captured_at"})[
        ["market_id", "selection_id", "mark_captured_at", "mark_price", "mark_source"]
    ]


def snapshot_rows_from_market(snapshot: MarketSnapshot) -> list[dict]:
    return flatten_market_snapshots([snapshot], captured_at=snapshot.captured_at)


def snapshot_payload(snapshot: MarketSnapshot) -> dict:
    payload = asdict(snapshot)
    payload["captured_at"] = (
        snapshot.captured_at.isoformat() if snapshot.captured_at else datetime.now(timezone.utc).isoformat()
    )
    return payload
