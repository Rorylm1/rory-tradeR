from __future__ import annotations

import os
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from src.exchanges import BetfairAdapter
from src.trading.accounting import calculate_realized_pnl, journal_performance_summary
from src.trading.journal import JournalStore

SETTLEMENT_MIN_AGE_HOURS_ENV_VAR = "RORY_TRADER_SETTLEMENT_MIN_AGE_HOURS"
SETTLEMENT_MAX_MARKETS_ENV_VAR = "RORY_TRADER_SETTLEMENT_MAX_MARKETS"
SETTLEMENT_MAX_POSITIONS_ENV_VAR = "RORY_TRADER_SETTLEMENT_MAX_POSITIONS"
DEFAULT_SETTLEMENT_MIN_AGE_HOURS = 3.0
DEFAULT_SETTLEMENT_MAX_MARKETS = 50
DEFAULT_SETTLEMENT_MAX_POSITIONS = 500

RUNNER_STATUS_OUTCOMES = {
    "WINNER": "won",
    "WON": "won",
    "LOSER": "lost",
    "LOST": "lost",
    "REMOVED": "void",
    "REMOVED_VACANT": "void",
}


@dataclass
class SettlementConfig:
    dry_run: bool = True
    min_age_hours: float = DEFAULT_SETTLEMENT_MIN_AGE_HOURS
    max_markets: int = DEFAULT_SETTLEMENT_MAX_MARKETS
    max_positions: int = DEFAULT_SETTLEMENT_MAX_POSITIONS


def settlement_config_from_env(*, dry_run: bool = True) -> SettlementConfig:
    return SettlementConfig(
        dry_run=dry_run,
        min_age_hours=_float_env(SETTLEMENT_MIN_AGE_HOURS_ENV_VAR, DEFAULT_SETTLEMENT_MIN_AGE_HOURS),
        max_markets=_int_env(SETTLEMENT_MAX_MARKETS_ENV_VAR, DEFAULT_SETTLEMENT_MAX_MARKETS),
        max_positions=_int_env(SETTLEMENT_MAX_POSITIONS_ENV_VAR, DEFAULT_SETTLEMENT_MAX_POSITIONS),
    )


def settlement_due_positions(
    summary: dict[str, pd.DataFrame],
    *,
    now: datetime | None = None,
    min_age_hours: float | None = None,
    max_markets: int | None = None,
    max_positions: int | None = None,
) -> pd.DataFrame:
    positions = summary.get("open_positions", pd.DataFrame())
    if positions.empty or "event_start" not in positions.columns:
        return pd.DataFrame()

    now = _utc(now)
    min_age_hours = (
        min_age_hours
        if min_age_hours is not None
        else _float_env(SETTLEMENT_MIN_AGE_HOURS_ENV_VAR, DEFAULT_SETTLEMENT_MIN_AGE_HOURS)
    )
    cutoff = now - timedelta(hours=min_age_hours)
    event_starts = pd.to_datetime(positions["event_start"], utc=True, errors="coerce")
    due = positions[event_starts.notna() & (event_starts <= cutoff)].copy()
    if due.empty:
        return due

    if "exchange" in due.columns:
        due = due[due["exchange"].astype(str).str.lower() == "betfair"].copy()
    if due.empty:
        return due

    sort_columns = [column for column in ["event_start", "market_id", "selection_id", "proposal_id"] if column in due]
    if sort_columns:
        due = due.sort_values(sort_columns)

    if max_markets is not None:
        market_ids = list(dict.fromkeys(due["market_id"].astype(str)))[:max_markets]
        due = due[due["market_id"].astype(str).isin(market_ids)].copy()

    if max_positions is not None:
        due = due.head(max_positions).copy()
    return due


def settle_due_positions(
    *,
    adapter: BetfairAdapter | None = None,
    journal_path: Path | None = None,
    dry_run: bool = True,
    min_age_hours: float | None = None,
    max_markets: int | None = None,
    max_positions: int | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    config = settlement_config_from_env(dry_run=dry_run)
    min_age_hours = min_age_hours if min_age_hours is not None else config.min_age_hours
    max_markets = max_markets if max_markets is not None else config.max_markets
    max_positions = max_positions if max_positions is not None else config.max_positions
    now = _utc(now)

    summary = journal_performance_summary(path=journal_path)
    due = settlement_due_positions(
        summary,
        now=now,
        min_age_hours=min_age_hours,
        max_markets=max_markets,
        max_positions=max_positions,
    )
    market_ids = list(dict.fromkeys(due["market_id"].astype(str))) if not due.empty else []
    adapter = adapter or BetfairAdapter()
    books = adapter.list_market_books(market_ids) if market_ids else []
    books_by_market_id = {str(book.get("marketId")): book for book in books if book.get("marketId") is not None}

    journal = JournalStore(path=journal_path)
    candidates: list[dict[str, Any]] = []
    skipped_reasons: Counter[str] = Counter()
    market_status_counts: Counter[str] = Counter()
    runner_status_counts: Counter[str] = Counter()
    settled_positions = 0

    for record in due.to_dict(orient="records"):
        market_id = str(record.get("market_id"))
        selection_id = str(record.get("selection_id"))
        book = books_by_market_id.get(market_id)
        if book is None:
            skipped_reasons["market_book_missing"] += 1
            continue

        market_status = str(book.get("status") or "UNKNOWN").upper()
        market_status_counts[market_status] += 1
        if market_status != "CLOSED":
            skipped_reasons["market_not_closed"] += 1
            continue

        runner = _runner_for_selection(book, selection_id)
        if runner is None:
            skipped_reasons["runner_missing"] += 1
            continue

        runner_status = str(runner.get("status") or "UNKNOWN").upper()
        runner_status_counts[runner_status] += 1
        outcome = RUNNER_STATUS_OUTCOMES.get(runner_status)
        if outcome is None:
            skipped_reasons["runner_status_not_settleable"] += 1
            continue

        realized_pnl = calculate_realized_pnl(
            side=str(record.get("side")),
            stake=float(record.get("stake")),
            fill_price=float(record.get("fill_price")),
            commission_paid=float(record.get("commission_paid") or 0.0),
            outcome=outcome,
        )
        candidate = _candidate_payload(
            record,
            market_status=market_status,
            runner_status=runner_status,
            outcome=outcome,
            realized_pnl=realized_pnl,
        )
        if not dry_run:
            journal.record_resolution(
                str(record["proposal_id"]),
                outcome,
                realized_pnl=realized_pnl,
                note=f"Betfair market book settlement: market_status={market_status} runner_status={runner_status}",
                resolved_at=now,
                source="betfair_market_book",
            )
            settled_positions += 1
            candidate["applied"] = True
        candidates.append(candidate)

    cutoff = now - timedelta(hours=min_age_hours)
    return {
        "dry_run": dry_run,
        "checked_at": now.isoformat(),
        "settlement_cutoff": cutoff.isoformat(),
        "min_age_hours": min_age_hours,
        "max_markets": max_markets,
        "max_positions": max_positions,
        "due_positions": int(len(due)),
        "checked_markets": len(market_ids),
        "market_books_returned": len(books_by_market_id),
        "settleable_positions": len(candidates),
        "settled_positions": settled_positions,
        "skipped_positions": int(len(due) - len(candidates)),
        "skipped_reasons": dict(skipped_reasons),
        "market_status_counts": dict(market_status_counts),
        "runner_status_counts": dict(runner_status_counts),
        "candidates": candidates,
        "live_execution_available": False,
    }


def _candidate_payload(
    record: dict[str, Any],
    *,
    market_status: str,
    runner_status: str,
    outcome: str,
    realized_pnl: float,
) -> dict[str, Any]:
    return {
        "proposal_id": _json_safe(record.get("proposal_id")),
        "market_id": _json_safe(record.get("market_id")),
        "selection_id": _json_safe(record.get("selection_id")),
        "event_name": _json_safe(record.get("event_name")),
        "market_title": _json_safe(record.get("market_title")),
        "selection_name": _json_safe(record.get("selection_name")),
        "event_start": _json_safe(record.get("event_start")),
        "side": _json_safe(record.get("side")),
        "stake": _json_safe(record.get("stake")),
        "fill_price": _json_safe(record.get("fill_price")),
        "market_status": market_status,
        "runner_status": runner_status,
        "resolved_outcome": outcome,
        "realized_pnl": realized_pnl,
        "applied": False,
    }


def _runner_for_selection(book: dict[str, Any], selection_id: str) -> dict[str, Any] | None:
    for runner in book.get("runners") or []:
        if str(runner.get("selectionId")) == selection_id:
            return runner
    return None


def _json_safe(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, pd.Timestamp):
        if pd.isna(value):
            return None
        return value.isoformat()
    if isinstance(value, datetime):
        return value.isoformat()
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        return value
    return value


def _utc(value: datetime | None) -> datetime:
    value = value or datetime.now(timezone.utc)
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _float_env(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    try:
        return float(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be numeric.") from exc


def _int_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer.") from exc
    if value < 1:
        raise ValueError(f"{name} must be at least 1.")
    return value
