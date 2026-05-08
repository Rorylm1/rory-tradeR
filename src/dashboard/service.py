from __future__ import annotations

import math
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from src.common.paths import runtime_path
from src.exchanges import BetfairAdapter
from src.trading.journal import JournalStore, journal_dataframe, journal_performance_summary
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


def _with_strategy_counts(overview: dict[str, Any], evaluation: dict[str, Any] | None) -> dict[str, Any]:
    overview = dict(overview)
    overview["latest_strategy_decisions"] = int(evaluation.get("decisions_count", 0)) if evaluation else 0
    overview["latest_strategy_acceptances"] = int(evaluation.get("accepted_count", 0)) if evaluation else 0
    overview["latest_strategy_rejections"] = int(evaluation.get("rejected_count", 0)) if evaluation else 0
    overview["latest_strategy_snapshots_seen"] = int(evaluation.get("snapshots_seen", 0)) if evaluation else 0
    return overview


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
    strategy_evaluation = latest_strategy_evaluation(store=store)
    latest_reviews = store.latest_live_reviews()
    open_positions = _records(summary["open_positions"])
    closed_positions = _records(summary["closed_positions"])

    for row in open_positions + closed_positions:
        review = latest_reviews.get(str(row.get("proposal_id")))
        row["live_review"] = review

    return {
        "overview": _with_strategy_counts(_overview_row(summary), strategy_evaluation),
        "open_positions": open_positions,
        "closed_positions": closed_positions,
        "recent_events": recent_events(store=store),
        "strategy_evaluation": strategy_evaluation,
        "strategy_decisions": recent_strategy_decisions(store=store),
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


def latest_markets(limit: int = 120) -> dict[str, Any]:
    path = latest_snapshot_path()
    if path is None:
        return {
            "snapshot_path": None,
            "captured_at": None,
            "market_count": 0,
            "selection_count": 0,
            "markets": [],
        }

    df = pd.read_parquet(path)
    if df.empty:
        return {
            "snapshot_path": str(path),
            "captured_at": None,
            "market_count": 0,
            "selection_count": 0,
            "markets": [],
        }

    if "captured_at" in df.columns:
        df["captured_at"] = pd.to_datetime(df["captured_at"], utc=True, errors="coerce")
    if "event_start" in df.columns:
        df["event_start"] = pd.to_datetime(df["event_start"], utc=True, errors="coerce")

    sort_columns = [column for column in ["event_start", "market_id", "selection_name"] if column in df.columns]
    rows = df.sort_values(sort_columns).head(limit).copy() if sort_columns else df.head(limit).copy()
    captured_at = df["captured_at"].max() if "captured_at" in df.columns else None

    return {
        "snapshot_path": str(path),
        "captured_at": _json_safe(captured_at),
        "market_count": int(df["market_id"].nunique()) if "market_id" in df.columns else 0,
        "selection_count": len(df),
        "markets": _records(rows),
    }


def pnl_series(store: DashboardStore | None = None) -> dict[str, Any]:
    store = store or DashboardStore()
    df = journal_dataframe(path=store.journal_path)
    if df.empty:
        return {"points": []}

    if "recorded_at" not in df.columns:
        return {"points": []}

    rows = df.sort_values("recorded_at").copy()
    realized = 0.0
    stake = 0.0
    points: list[dict[str, Any]] = []

    for _, row in rows.iterrows():
        event_type = row.get("event_type")
        accepted = row.get("accepted")
        if event_type == "execution" and pd.notna(accepted) and bool(accepted) and pd.notna(row.get("stake")):
            stake += float(row.get("stake"))
        elif event_type == "resolution" and pd.notna(row.get("realized_pnl")):
            realized += float(row.get("realized_pnl"))
        else:
            continue

        points.append(
            {
                "recorded_at": _json_safe(row.get("recorded_at")),
                "event_type": event_type,
                "cumulative_realized_pnl": round(realized, 4),
                "cumulative_stake": round(stake, 4),
            }
        )

    return {"points": points}


def latest_strategy_evaluation(store: DashboardStore | None = None) -> dict[str, Any] | None:
    store = store or DashboardStore()
    events = JournalStore(path=store.journal_path).load_events()
    for row in reversed(events):
        if row.get("event_type") != "strategy_evaluation":
            continue
        payload = dict(row.get("payload", {}))
        payload.pop("decisions", None)
        payload["recorded_at"] = row.get("recorded_at")
        return payload
    return None


def recent_strategy_decisions(store: DashboardStore | None = None, limit: int = 25) -> list[dict[str, Any]]:
    store = store or DashboardStore()
    events = JournalStore(path=store.journal_path).load_events()
    for row in reversed(events):
        if row.get("event_type") != "strategy_evaluation":
            continue
        decisions = row.get("payload", {}).get("decisions", [])
        if not isinstance(decisions, list):
            return []
        return [
            {
                **decision,
                "recorded_at": row.get("recorded_at"),
            }
            for decision in decisions[:limit]
            if isinstance(decision, dict)
        ]
    return []


def runtime_database_path() -> Path:
    return runtime_path("dashboard", "dashboard.sqlite")
