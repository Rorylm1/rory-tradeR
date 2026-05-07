from __future__ import annotations

import math
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from src.common.paths import runtime_path
from src.exchanges import BetfairAdapter
from src.trading.journal import JournalStore, journal_performance_summary
from src.trading.market_history import latest_snapshot_path

from .store import DashboardStore

LIVE_ENABLED_ENV_VAR = "RORY_TRADER_LIVE_ENABLED"
STALE_AFTER_SECONDS_ENV_VAR = "RORY_TRADER_DASHBOARD_STALE_AFTER_SECONDS"
DEFAULT_STALE_AFTER_SECONDS = 30 * 60


def _json_safe(value: Any) -> Any:
    if isinstance(value, pd.Timestamp):
        if pd.isna(value):
            return None
        return value.isoformat()
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    if value is pd.NA or pd.isna(value):
        return None
    if isinstance(value, Path):
        return str(value)
    return value


def _records(df: pd.DataFrame, limit: int | None = None) -> list[dict[str, Any]]:
    if df.empty:
        return []
    if limit is not None:
        df = df.head(limit)
    rows: list[dict[str, Any]] = []
    for record in df.to_dict(orient="records"):
        rows.append({key: _json_safe(value) for key, value in record.items()})
    return rows


def _overview_row(summary: dict[str, pd.DataFrame]) -> dict[str, Any]:
    overview = summary["overview"]
    if overview.empty:
        return {
            "journal_events": len(summary["events"]),
            "executed_positions": 0,
            "open_positions": 0,
            "closed_positions": 0,
            "won_positions": 0,
            "lost_positions": 0,
            "void_positions": 0,
            "marked_open_positions": 0,
            "total_stake": 0.0,
            "total_commission_paid": 0.0,
            "total_realized_pnl": 0.0,
            "total_unrealized_pnl": 0.0,
            "total_net_pnl": 0.0,
        }
    return {key: _json_safe(value) for key, value in overview.iloc[0].to_dict().items()}


def _latest_snapshot_status(stale_after_seconds: int) -> dict[str, Any]:
    path = latest_snapshot_path()
    if path is None:
        return {
            "latest_snapshot_path": None,
            "latest_snapshot_modified_at": None,
            "snapshot_age_seconds": None,
            "stale": True,
            "stale_after_seconds": stale_after_seconds,
        }

    modified_at = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
    age_seconds = (datetime.now(timezone.utc) - modified_at).total_seconds()
    return {
        "latest_snapshot_path": str(path),
        "latest_snapshot_modified_at": modified_at.isoformat(),
        "snapshot_age_seconds": round(age_seconds, 3),
        "stale": age_seconds > stale_after_seconds,
        "stale_after_seconds": stale_after_seconds,
    }


def dashboard_summary(store: DashboardStore | None = None) -> dict[str, Any]:
    store = store or DashboardStore()
    synced_events = store.sync_journal()
    summary = journal_performance_summary(path=store.journal_path)
    latest_reviews = store.latest_live_reviews()
    open_positions = _records(summary["open_positions"])
    closed_positions = _records(summary["closed_positions"])

    for row in open_positions + closed_positions:
        review = latest_reviews.get(str(row.get("proposal_id")))
        row["live_review"] = review

    return {
        "overview": _overview_row(summary),
        "open_positions": open_positions,
        "closed_positions": closed_positions,
        "recent_events": recent_events(store=store),
        "synced_events": synced_events,
        "journal_path": str(store.journal_path),
        "database_path": str(store.db_path),
        "live_execution_available": False,
        "live_enabled": os.getenv(LIVE_ENABLED_ENV_VAR, "false").lower() == "true",
    }


def dashboard_health(store: DashboardStore | None = None, validate_betfair: bool = True) -> dict[str, Any]:
    store = store or DashboardStore()
    store.sync_journal()
    stale_after_seconds = int(os.getenv(STALE_AFTER_SECONDS_ENV_VAR, str(DEFAULT_STALE_AFTER_SECONDS)))
    adapter = BetfairAdapter()
    validation_payload: dict[str, Any]
    if validate_betfair:
        validation = adapter.validate_credentials()
        validation_payload = {
            "exchange": validation.exchange,
            "ok": validation.ok,
            "approval_status": validation.approval_status,
            "message": validation.message,
        }
    else:
        validation_payload = {
            "exchange": adapter.name,
            "ok": None,
            "approval_status": "not_checked",
            "message": "Betfair validation was skipped.",
        }

    return {
        "status": "ok",
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "betfair": validation_payload,
        "snapshots": _latest_snapshot_status(stale_after_seconds),
        "journal_path": str(store.journal_path),
        "database_path": str(store.db_path),
        "supports_live_execution": adapter.supports_live_execution,
        "live_enabled": os.getenv(LIVE_ENABLED_ENV_VAR, "false").lower() == "true",
        "live_execution_available": False,
    }


def dashboard_overview(store: DashboardStore | None = None) -> dict[str, Any]:
    summary = dashboard_summary(store=store)
    return {
        "overview": summary["overview"],
        "journal_path": summary["journal_path"],
        "database_path": summary["database_path"],
        "live_execution_available": False,
        "live_enabled": summary["live_enabled"],
    }


def open_positions(store: DashboardStore | None = None) -> list[dict[str, Any]]:
    return dashboard_summary(store=store)["open_positions"]


def closed_positions(store: DashboardStore | None = None) -> list[dict[str, Any]]:
    return dashboard_summary(store=store)["closed_positions"]


def recent_events(store: DashboardStore | None = None, limit: int = 25) -> list[dict[str, Any]]:
    store = store or DashboardStore()
    events = JournalStore(path=store.journal_path).load_events()
    rows = list(reversed(events[-limit:]))
    return [
        {
            "event_type": row.get("event_type"),
            "recorded_at": row.get("recorded_at"),
            "payload": row.get("payload", {}),
        }
        for row in rows
    ]


def runtime_database_path() -> Path:
    return runtime_path("dashboard", "dashboard.sqlite")
