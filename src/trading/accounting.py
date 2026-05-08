from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from src.trading.journal import JournalStore, journal_dataframe
from src.trading.market_history import latest_snapshot_marks

RESOLVED_OUTCOMES = {"won", "lost", "void"}


def normalize_resolution_outcome(outcome: str) -> str:
    normalized = outcome.strip().lower()
    aliases = {
        "win": "won",
        "won": "won",
        "yes": "won",
        "loss": "lost",
        "lose": "lost",
        "lost": "lost",
        "no": "lost",
        "void": "void",
        "push": "void",
        "cancelled": "void",
        "canceled": "void",
    }
    resolved = aliases.get(normalized)
    if resolved is None:
        allowed = ", ".join(sorted(RESOLVED_OUTCOMES))
        raise ValueError(f"Unsupported outcome '{outcome}'. Use one of: {allowed}.")
    return resolved


def calculate_realized_pnl(
    *,
    side: str,
    stake: float,
    fill_price: float,
    commission_paid: float = 0.0,
    outcome: str,
) -> float:
    normalized_outcome = normalize_resolution_outcome(outcome)
    if side != "back":
        raise ValueError(f"Realized PnL is only implemented for back positions. Unsupported side: {side}")

    if normalized_outcome == "won":
        pnl = stake * (fill_price - 1.0) - commission_paid
    elif normalized_outcome == "lost":
        pnl = -stake - commission_paid
    else:
        pnl = -commission_paid

    return round(pnl, 4)


def calculate_unrealized_pnl(
    *,
    side: str,
    stake: float,
    fill_price: float,
    current_exit_price: float | None,
    commission_paid: float = 0.0,
) -> float | None:
    if current_exit_price is None or current_exit_price <= 1.0:
        return None
    if side != "back":
        return None

    cash_out_pnl = stake * ((fill_price / current_exit_price) - 1.0) - commission_paid
    return round(cash_out_pnl, 4)


def _empty_summary(events: pd.DataFrame) -> dict[str, pd.DataFrame]:
    empty = pd.DataFrame()
    return {
        "events": events,
        "overview": empty,
        "positions": empty,
        "open_positions": empty,
        "closed_positions": empty,
        "strategy": empty,
        "price_bucket": empty,
        "time_window": empty,
    }


def _sum_or_zero(series: pd.Series) -> float:
    if series.empty:
        return 0.0
    value = series.sum(min_count=1)
    if pd.isna(value):
        return 0.0
    return float(value)


def _build_positions(path: Path | None = None, snapshot_dir: Path | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    df = journal_dataframe(path=path)
    if df.empty:
        return df, pd.DataFrame()

    proposals = df[df["event_type"] == "proposal"].copy()
    if "accepted" not in df.columns:
        return df, pd.DataFrame()

    executions = df[(df["event_type"] == "execution") & (df["accepted"] == True)].copy()  # noqa: E712
    resolutions = df[df["event_type"] == "resolution"].copy()

    if proposals.empty or executions.empty:
        return df, pd.DataFrame()

    proposal_columns = [
        "proposal_id",
        "created_at",
        "strategy_name",
        "strategy_version",
        "exchange",
        "market_id",
        "selection_id",
        "market_title",
        "selection_name",
        "category",
        "subcategory",
        "event_start",
        "event_name",
        "competition_name",
        "side",
        "stake",
        "requested_price",
        "best_back",
        "best_lay",
        "last_traded",
        "signal_confidence",
        "reason",
        "holding_period_hours",
    ]
    proposals = proposals[[column for column in proposal_columns if column in proposals.columns]].copy()

    execution_columns = [
        "proposal_id",
        "mode",
        "exchange",
        "message",
        "fill_price",
        "commission_paid",
        "slippage_paid",
        "fill_timestamp",
        "stake",
        "side",
    ]
    executions = executions[[column for column in execution_columns if column in executions.columns]].copy()
    executions = executions.rename(
        columns={
            "stake": "filled_stake",
            "side": "fill_side",
            "exchange": "execution_exchange",
            "message": "execution_message",
        }
    )

    positions = proposals.merge(executions, on="proposal_id", how="inner")
    if positions.empty:
        return df, pd.DataFrame()

    if not resolutions.empty:
        resolution_columns = [
            "proposal_id",
            "resolved_outcome",
            "realized_pnl",
            "resolved_at",
            "resolution_note",
            "resolution_source",
        ]
        resolutions = resolutions[[column for column in resolution_columns if column in resolutions.columns]].copy()
        resolutions = resolutions.sort_values("resolved_at").drop_duplicates("proposal_id", keep="last")
        positions = positions.merge(resolutions, on="proposal_id", how="left")
    else:
        positions["resolved_outcome"] = pd.NA
        positions["realized_pnl"] = pd.NA
        positions["resolved_at"] = pd.NaT
        positions["resolution_note"] = pd.NA
        positions["resolution_source"] = pd.NA

    positions["stake"] = positions["filled_stake"].fillna(positions["stake"])
    positions["side"] = positions["fill_side"].fillna(positions["side"])
    positions["commission_paid"] = positions["commission_paid"].fillna(0.0)
    positions["slippage_paid"] = positions["slippage_paid"].fillna(0.0)
    positions["closed_position"] = positions["resolved_outcome"].notna()
    positions["won_position"] = positions["resolved_outcome"] == "won"
    positions["lost_position"] = positions["resolved_outcome"] == "lost"
    positions["void_position"] = positions["resolved_outcome"] == "void"
    positions["open_position"] = ~positions["closed_position"]

    positions["price_bucket"] = pd.cut(
        positions["requested_price"],
        bins=[0, 1.5, 2.0, 3.0, 5.0, 10.0, 100.0],
        labels=["<=1.5", "1.5-2.0", "2.0-3.0", "3.0-5.0", "5.0-10.0", "10.0+"],
        include_lowest=True,
    )
    positions["hours_to_event"] = (
        (positions["event_start"] - positions["created_at"]).dt.total_seconds() / 3600
    )
    positions["time_window"] = pd.cut(
        positions["hours_to_event"],
        bins=[0, 6, 12, 24, 48, 96, 999999],
        labels=["0-6h", "6-12h", "12-24h", "24-48h", "48-96h", "96h+"],
        include_lowest=True,
    )

    marks = latest_snapshot_marks(snapshot_dir=snapshot_dir)
    if not marks.empty:
        positions = positions.merge(marks, on=["market_id", "selection_id"], how="left")
    else:
        positions["mark_price"] = pd.NA
        positions["mark_source"] = pd.NA
        positions["mark_captured_at"] = pd.NaT

    positions["unrealized_pnl"] = positions.apply(
        lambda row: calculate_unrealized_pnl(
            side=row["side"],
            stake=float(row["stake"]),
            fill_price=float(row["fill_price"]),
            current_exit_price=float(row["mark_price"]) if pd.notna(row["mark_price"]) else None,
            commission_paid=float(row["commission_paid"]),
        )
        if row["open_position"] and pd.notna(row["fill_price"])
        else None,
        axis=1,
    )

    return df, positions


def journal_performance_summary(path: Path | None = None, snapshot_dir: Path | None = None) -> dict[str, pd.DataFrame]:
    events, positions = _build_positions(path=path, snapshot_dir=snapshot_dir)
    if positions.empty:
        return _empty_summary(events)

    open_positions = positions[positions["open_position"]].copy()
    closed_positions = positions[positions["closed_position"]].copy()

    overview = pd.DataFrame(
        [
            {
                "journal_events": len(events),
                "executed_positions": len(positions),
                "open_positions": int(positions["open_position"].sum()),
                "closed_positions": int(positions["closed_position"].sum()),
                "won_positions": int(positions["won_position"].sum()),
                "lost_positions": int(positions["lost_position"].sum()),
                "void_positions": int(positions["void_position"].sum()),
                "marked_open_positions": int(open_positions["unrealized_pnl"].notna().sum()),
                "total_stake": round(_sum_or_zero(positions["stake"]), 4),
                "total_commission_paid": round(_sum_or_zero(positions["commission_paid"]), 4),
                "total_realized_pnl": round(_sum_or_zero(closed_positions["realized_pnl"]), 4),
                "total_unrealized_pnl": round(_sum_or_zero(open_positions["unrealized_pnl"].dropna()), 4),
            }
        ]
    )
    overview["total_net_pnl"] = overview["total_realized_pnl"] + overview["total_unrealized_pnl"]

    def grouped_summary(group_by: list[str]) -> pd.DataFrame:
        grouped = (
            positions.groupby(group_by, dropna=False, observed=False)
            .agg(
                executed_positions=("proposal_id", "count"),
                open_positions=("open_position", "sum"),
                closed_positions=("closed_position", "sum"),
                won_positions=("won_position", "sum"),
                avg_confidence=("signal_confidence", "mean"),
                total_stake=("stake", "sum"),
                total_commission_paid=("commission_paid", "sum"),
                total_realized_pnl=("realized_pnl", "sum"),
                total_unrealized_pnl=("unrealized_pnl", "sum"),
            )
            .reset_index()
        )
        grouped["win_rate"] = grouped.apply(
            lambda row: (row["won_positions"] / row["closed_positions"]) if row["closed_positions"] else pd.NA,
            axis=1,
        )
        realized = pd.to_numeric(grouped["total_realized_pnl"], errors="coerce").fillna(0.0)
        unrealized = pd.to_numeric(grouped["total_unrealized_pnl"], errors="coerce").fillna(0.0)
        grouped["total_net_pnl"] = realized + unrealized
        return grouped

    strategy = grouped_summary(["strategy_name", "strategy_version"])
    price_bucket = grouped_summary(["price_bucket"])
    time_window = grouped_summary(["time_window"])

    return {
        "events": events,
        "overview": overview,
        "positions": positions,
        "open_positions": open_positions,
        "closed_positions": closed_positions,
        "strategy": strategy,
        "price_bucket": price_bucket,
        "time_window": time_window,
    }


def resolve_journal_position(
    proposal_id: str,
    outcome: str,
    *,
    path: Path | None = None,
    snapshot_dir: Path | None = None,
    note: str = "",
    source: str = "manual",
) -> dict[str, object]:
    normalized_outcome = normalize_resolution_outcome(outcome)
    summary = journal_performance_summary(path=path, snapshot_dir=snapshot_dir)
    positions = summary["positions"]

    if positions.empty:
        raise ValueError("No executed paper positions exist in the journal yet.")

    matching = positions[positions["proposal_id"] == proposal_id]
    if matching.empty:
        raise ValueError(f"Proposal {proposal_id} was not found among executed paper positions.")

    position = matching.iloc[0]
    if pd.notna(position.get("resolved_outcome")):
        raise ValueError(f"Proposal {proposal_id} is already resolved as {position['resolved_outcome']}.")

    realized_pnl = calculate_realized_pnl(
        side=str(position["side"]),
        stake=float(position["stake"]),
        fill_price=float(position["fill_price"]),
        commission_paid=float(position["commission_paid"]),
        outcome=normalized_outcome,
    )

    JournalStore(path=path).record_resolution(
        proposal_id,
        normalized_outcome,
        realized_pnl=realized_pnl,
        note=note,
        resolved_at=datetime.now(timezone.utc),
        source=source,
    )

    return {
        "proposal_id": proposal_id,
        "resolved_outcome": normalized_outcome,
        "realized_pnl": realized_pnl,
        "market_title": position["market_title"],
        "selection_name": position["selection_name"],
        "strategy_name": position["strategy_name"],
        "strategy_version": position["strategy_version"],
    }
