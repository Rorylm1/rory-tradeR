from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from src.common.paths import data_path
from src.exchanges.common.models import MarketSnapshot, SelectionSnapshot


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
                    "best_back_size": selection.best_back_size,
                    "best_lay_size": selection.best_lay_size,
                    "traded_volume": selection.traded_volume,
                    "selection_total_matched": selection.total_matched,
                    "market_total_matched": snapshot.total_matched,
                    "market_total_available": snapshot.total_available,
                    "in_play": snapshot.in_play,
                    "is_market_data_delayed": snapshot.is_market_data_delayed,
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


def load_market_snapshots(path: Path | str) -> list[MarketSnapshot]:
    df = pd.read_parquet(path)
    if df.empty:
        return []

    for column in ("captured_at", "event_start"):
        if column in df.columns:
            df[column] = pd.to_datetime(df[column], utc=True, errors="coerce")

    snapshots: list[MarketSnapshot] = []
    for market_id, market_rows in df.groupby("market_id", sort=True, dropna=False):
        first = market_rows.sort_values(["captured_at", "selection_id"], na_position="last").iloc[0]
        captured_at = _clean_value(first.get("captured_at"))
        event_start = _clean_value(first.get("event_start"))
        selections = []
        for _, row in market_rows.sort_values("selection_id", na_position="last").iterrows():
            selections.append(
                SelectionSnapshot(
                    exchange=str(_clean_value(row.get("exchange")) or ""),
                    market_id=str(_clean_value(row.get("market_id")) or ""),
                    selection_id=str(_clean_value(row.get("selection_id")) or ""),
                    market_title=str(_clean_value(row.get("market_title")) or ""),
                    selection_name=str(_clean_value(row.get("selection_name")) or ""),
                    category=str(_clean_value(row.get("category")) or "unknown"),
                    subcategory=str(_clean_value(row.get("subcategory")) or "unknown"),
                    event_start=_clean_value(row.get("event_start")),
                    best_back=_clean_value(row.get("best_back")),
                    best_lay=_clean_value(row.get("best_lay")),
                    last_traded=_clean_value(row.get("last_traded")),
                    status=str(_clean_value(row.get("status")) or "unknown"),
                    event_name=_clean_value(row.get("event_name")),
                    competition_name=_clean_value(row.get("competition_name")),
                    captured_at=_clean_value(row.get("captured_at")),
                    best_back_size=_clean_value(row.get("best_back_size")),
                    best_lay_size=_clean_value(row.get("best_lay_size")),
                    traded_volume=_clean_value(row.get("traded_volume")),
                    total_matched=_clean_value(row.get("selection_total_matched")),
                )
            )

        snapshots.append(
            MarketSnapshot(
                exchange=str(_clean_value(first.get("exchange")) or ""),
                market_id=str(_clean_value(market_id) or ""),
                market_title=str(_clean_value(first.get("market_title")) or ""),
                category=str(_clean_value(first.get("category")) or "unknown"),
                subcategory=str(_clean_value(first.get("subcategory")) or "unknown"),
                event_start=event_start,
                status=str(_clean_value(first.get("status")) or "unknown"),
                selections=selections,
                event_name=_clean_value(first.get("event_name")),
                competition_name=_clean_value(first.get("competition_name")),
                captured_at=captured_at,
                total_matched=_clean_value(first.get("market_total_matched")),
                total_available=_clean_value(first.get("market_total_available")),
                in_play=_clean_value(first.get("in_play")),
                is_market_data_delayed=_clean_value(first.get("is_market_data_delayed")),
            )
        )
    return snapshots


def snapshot_rows_from_market(snapshot: MarketSnapshot) -> list[dict]:
    return flatten_market_snapshots([snapshot], captured_at=snapshot.captured_at)


def snapshot_payload(snapshot: MarketSnapshot) -> dict:
    payload = asdict(snapshot)
    payload["captured_at"] = (
        snapshot.captured_at.isoformat() if snapshot.captured_at else datetime.now(timezone.utc).isoformat()
    )
    return payload


def _clean_value(value):
    if value is None or pd.isna(value):
        return None
    if isinstance(value, pd.Timestamp):
        return value.to_pydatetime()
    return value
