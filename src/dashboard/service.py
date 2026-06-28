from __future__ import annotations

import json
import math
import os
import re
import subprocess
from collections import deque
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any

import pandas as pd

from src.common.paths import REPO_ROOT, runtime_path
from src.exchanges import BetfairAdapter
from src.exchanges.common.models import MarketSnapshot
from src.trading.journal import JournalStore, journal_performance_summary
from src.trading.market_history import flatten_market_snapshots, latest_snapshot_path
from src.trading.strategy import strategy_for_category

from .store import DashboardStore

LIVE_ENABLED_ENV_VAR = "RORY_TRADER_LIVE_ENABLED"
STALE_AFTER_SECONDS_ENV_VAR = "RORY_TRADER_DASHBOARD_STALE_AFTER_SECONDS"
MIN_AVAILABLE_SIZE_ENV_VAR = "RORY_TRADER_DASHBOARD_MIN_AVAILABLE_SIZE"
MIN_MARKET_TOTAL_MATCHED_ENV_VAR = "RORY_TRADER_DASHBOARD_MIN_MARKET_TOTAL_MATCHED"
DEFAULT_STALE_AFTER_SECONDS = 30 * 60
DEFAULT_MIN_AVAILABLE_SIZE = 2.0
DEFAULT_MIN_MARKET_TOTAL_MATCHED = 100.0
PAPER_SESSION_TIMEOUT_ENV_VAR = "RORY_TRADER_PAPER_SESSION_TIMEOUT_SECONDS"
DEFAULT_PAPER_SESSION_TIMEOUT_SECONDS = 300
_SUMMARY_CACHE_LOCK = Lock()
_SUMMARY_CACHE: tuple[tuple[object, ...], dict[str, pd.DataFrame]] | None = None


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


def _float_or_none(value: Any) -> float | None:
    if value is None:
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(parsed) or math.isinf(parsed):
        return None
    return parsed


def _iter_journal_events(path: Path, event_types: set[str] | None = None):
    if not path.exists():
        return

    needles = None
    if event_types is not None:
        needles = [f'"event_type": "{event_type}"' for event_type in event_types]

    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            if needles is not None and not any(needle in line for needle in needles):
                continue
            yield json.loads(line)


def _records(df: pd.DataFrame, limit: int | None = None) -> list[dict[str, Any]]:
    if df.empty:
        return []
    if limit is not None:
        df = df.head(limit)
    rows: list[dict[str, Any]] = []
    for record in df.to_dict(orient="records"):
        rows.append({key: _json_safe(value) for key, value in record.items()})
    return rows


def _non_empty_performance_records(df: pd.DataFrame) -> list[dict[str, Any]]:
    if df.empty or "executed_positions" not in df.columns:
        return []
    executed = pd.to_numeric(df["executed_positions"], errors="coerce").fillna(0)
    return _records(df[executed > 0])


def _has_json_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, (dict, list)):
        return True
    try:
        return not bool(pd.isna(value))
    except (TypeError, ValueError):
        return True


def _file_fingerprint(path: Path | None) -> tuple[str | None, int | None, int | None]:
    if path is None:
        return (None, None, None)
    try:
        stat = path.stat()
    except FileNotFoundError:
        return (str(path), None, None)
    return (str(path), stat.st_mtime_ns, stat.st_size)


def _cached_journal_summary(store: DashboardStore) -> dict[str, pd.DataFrame]:
    global _SUMMARY_CACHE

    snapshot_path = latest_snapshot_path()
    cache_key = (
        _file_fingerprint(store.journal_path),
        _file_fingerprint(snapshot_path),
    )
    with _SUMMARY_CACHE_LOCK:
        if _SUMMARY_CACHE is not None and _SUMMARY_CACHE[0] == cache_key:
            return _SUMMARY_CACHE[1]

    summary = journal_performance_summary(path=store.journal_path)
    with _SUMMARY_CACHE_LOCK:
        _SUMMARY_CACHE = (cache_key, summary)
    return summary


def _performance_breakdown_from_summary(summary: dict[str, pd.DataFrame]) -> dict[str, Any]:
    return {
        "strategy": _non_empty_performance_records(summary["strategy"]),
        "price_bucket": _non_empty_performance_records(summary["price_bucket"]),
        "time_window": _non_empty_performance_records(summary["time_window"]),
    }


def _recent_events_from_frame(events: pd.DataFrame, limit: int = 25) -> list[dict[str, Any]]:
    if events.empty:
        return []
    rows = events.tail(limit).iloc[::-1]
    return [
        {
            "event_type": row.get("event_type"),
            "recorded_at": _json_safe(row.get("recorded_at")),
            "payload": {},
        }
        for _, row in rows.iterrows()
    ]


def _latest_strategy_evaluation_from_frame(events: pd.DataFrame) -> dict[str, Any] | None:
    if events.empty or "event_type" not in events.columns:
        return None
    rows = events[events["event_type"] == "strategy_evaluation"]
    if rows.empty:
        return None

    row = rows.iloc[-1].to_dict()
    row.pop("decisions", None)
    return {key: _json_safe(value) for key, value in row.items() if _has_json_value(value)}


def _recent_strategy_decisions_from_frame(events: pd.DataFrame, limit: int = 25) -> list[dict[str, Any]]:
    if events.empty or "event_type" not in events.columns:
        return []
    rows = events[events["event_type"] == "strategy_evaluation"]
    if rows.empty:
        return []

    row = rows.iloc[-1]
    decisions = row.get("decisions")
    if not isinstance(decisions, list):
        return []
    return [
        {
            **decision,
            "recorded_at": _json_safe(row.get("recorded_at")),
        }
        for decision in decisions[:limit]
        if isinstance(decision, dict)
    ]


def _plain_json(value: Any) -> Any:
    if isinstance(value, tuple):
        return [_plain_json(item) for item in value]
    if isinstance(value, list):
        return [_plain_json(item) for item in value]
    if isinstance(value, dict):
        return {key: _plain_json(item) for key, item in value.items()}
    return value


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


def _data_quality_from_frame(
    df: pd.DataFrame,
    *,
    min_available_size: float | None = None,
    min_market_total_matched: float | None = None,
) -> dict[str, Any]:
    min_available_size = (
        min_available_size
        if min_available_size is not None
        else float(os.getenv(MIN_AVAILABLE_SIZE_ENV_VAR, str(DEFAULT_MIN_AVAILABLE_SIZE)))
    )
    min_market_total_matched = (
        min_market_total_matched
        if min_market_total_matched is not None
        else float(os.getenv(MIN_MARKET_TOTAL_MATCHED_ENV_VAR, str(DEFAULT_MIN_MARKET_TOTAL_MATCHED)))
    )
    if df.empty:
        return {
            "market_count": 0,
            "selection_count": 0,
            "priced_selection_count": 0,
            "missing_price_count": 0,
            "liquid_selection_count": 0,
            "tradeable_selection_count": 0,
            "delayed_market_data_count": 0,
            "in_play_market_count": 0,
            "min_available_size": min_available_size,
            "min_market_total_matched": min_market_total_matched,
            "price_missing_kill_switch": True,
            "liquidity_kill_switch": True,
            "delayed_data_kill_switch": False,
            "in_play_kill_switch": False,
        }

    for column in [
        "best_back",
        "best_lay",
        "last_traded",
        "best_back_size",
        "best_lay_size",
        "market_total_matched",
    ]:
        if column not in df.columns:
            df[column] = pd.NA

    priced = df[["best_back", "best_lay", "last_traded"]].notna().any(axis=1)
    executable = df[["best_back", "best_lay"]].notna().all(axis=1)
    has_size = df["best_back_size"].isna() | (
        pd.to_numeric(df["best_back_size"], errors="coerce") >= min_available_size
    )
    has_market_liquidity = df["market_total_matched"].isna() | (
        pd.to_numeric(df["market_total_matched"], errors="coerce") >= min_market_total_matched
    )
    liquid = executable & has_size & has_market_liquidity

    delayed_count = 0
    if "is_market_data_delayed" in df.columns:
        delayed_count = int(df[df["is_market_data_delayed"] == True]["market_id"].nunique())  # noqa: E712
    in_play_count = 0
    if "in_play" in df.columns:
        in_play_count = int(df[df["in_play"] == True]["market_id"].nunique())  # noqa: E712

    market_count = int(df["market_id"].nunique()) if "market_id" in df.columns else 0
    selection_count = len(df)
    priced_count = int(priced.sum())
    liquid_count = int(liquid.sum())
    missing_price_count = selection_count - priced_count

    return {
        "market_count": market_count,
        "selection_count": selection_count,
        "priced_selection_count": priced_count,
        "missing_price_count": missing_price_count,
        "liquid_selection_count": liquid_count,
        "tradeable_selection_count": liquid_count,
        "delayed_market_data_count": delayed_count,
        "in_play_market_count": in_play_count,
        "min_available_size": min_available_size,
        "min_market_total_matched": min_market_total_matched,
        "price_missing_kill_switch": missing_price_count > 0,
        "liquidity_kill_switch": liquid_count == 0,
        "delayed_data_kill_switch": delayed_count > 0,
        "in_play_kill_switch": in_play_count > 0,
    }


def _snapshot_data_quality(
    path: Path | None = None,
    *,
    min_available_size: float | None = None,
    min_market_total_matched: float | None = None,
) -> dict[str, Any]:
    path = path or latest_snapshot_path()
    if path is None:
        return _data_quality_from_frame(
            pd.DataFrame(),
            min_available_size=min_available_size,
            min_market_total_matched=min_market_total_matched,
        )

    return _data_quality_from_frame(
        pd.read_parquet(path),
        min_available_size=min_available_size,
        min_market_total_matched=min_market_total_matched,
    )


def _market_rows_from_snapshots(snapshots: list[MarketSnapshot]) -> pd.DataFrame:
    rows = flatten_market_snapshots(snapshots, captured_at=datetime.now(timezone.utc))
    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    if "captured_at" in df.columns:
        df["captured_at"] = pd.to_datetime(df["captured_at"], utc=True, errors="coerce")
    if "event_start" in df.columns:
        df["event_start"] = pd.to_datetime(df["event_start"], utc=True, errors="coerce")
    return df


def _safe_error_message(exc: Exception) -> str:
    text = str(exc)
    if "TOO_MUCH_DATA" in text:
        return "Betfair live odds fetch failed: TOO_MUCH_DATA. Try fewer markets or a smaller book batch."
    if "INVALID_SESSION_INFORMATION" in text:
        return "Betfair live odds fetch failed: INVALID_SESSION_INFORMATION. Re-authentication is required."
    return f"Betfair live odds fetch failed: {exc.__class__.__name__}"


def dashboard_summary(
    store: DashboardStore | None = None,
    *,
    open_limit: int | None = None,
    closed_limit: int | None = None,
    recent_limit: int = 25,
    decision_limit: int = 25,
) -> dict[str, Any]:
    store = store or DashboardStore()
    summary = _cached_journal_summary(store)
    strategy_evaluation = _latest_strategy_evaluation_from_frame(summary["events"])
    latest_reviews = store.latest_live_reviews()
    open_positions = _records(summary["open_positions"], limit=open_limit)
    closed_positions = _records(summary["closed_positions"], limit=closed_limit)

    for row in open_positions + closed_positions:
        review = latest_reviews.get(str(row.get("proposal_id")))
        row["live_review"] = review

    return {
        "overview": _with_strategy_counts(_overview_row(summary), strategy_evaluation),
        "open_positions": open_positions,
        "closed_positions": closed_positions,
        "recent_events": _recent_events_from_frame(summary["events"], limit=recent_limit),
        "strategy_evaluation": strategy_evaluation,
        "strategy_decisions": _recent_strategy_decisions_from_frame(summary["events"], limit=decision_limit),
        "performance": _performance_breakdown_from_summary(summary),
        "synced_events": 0,
        "journal_path": str(store.journal_path),
        "database_path": str(store.db_path),
        "live_execution_available": False,
        "live_enabled": os.getenv(LIVE_ENABLED_ENV_VAR, "false").lower() == "true",
    }


def performance_breakdown(store: DashboardStore | None = None) -> dict[str, Any]:
    store = store or DashboardStore()
    summary = _cached_journal_summary(store)
    return _performance_breakdown_from_summary(summary)


def recent_snapshot_collections(store: DashboardStore | None = None, limit: int = 8) -> list[dict[str, Any]]:
    store = store or DashboardStore()
    snapshots: deque[dict[str, Any]] = deque(maxlen=limit)
    for row in _iter_journal_events(store.journal_path, {"snapshot_collection"}):
        payload = dict(row.get("payload", {}))
        payload["recorded_at"] = row.get("recorded_at")
        snapshots.append(payload)
    return list(reversed(snapshots))


def strategy_context(category: str = "tennis", store: DashboardStore | None = None) -> dict[str, Any]:
    strategy = strategy_for_category(category)
    definition = _plain_json(asdict(strategy.definition))
    return {
        "category": category,
        "definition": definition,
        "rules": [
            {
                "label": "Universe",
                "value": ", ".join(definition["allowed_subcategories"] or definition["allowed_categories"]),
                "detail": "Only matching markets can create proposals.",
            },
            {
                "label": "Price bucket",
                "value": f"{definition['min_back_price']:.2f} to {definition['max_back_price']:.2f}",
                "detail": "Best available back price must sit inside this range.",
            },
            {
                "label": "Spread cap",
                "value": f"{definition['max_spread']:.2f}",
                "detail": "Best lay minus best back must be no wider than this.",
            },
            {
                "label": "Event window",
                "value": f"{definition['min_hours_to_event']:.1f}h to {definition['max_hours_to_event']:.0f}h",
                "detail": "Avoids in-play/immediate starts and very distant events.",
            },
            {
                "label": "Market liquidity",
                "value": f"matched >= {definition['min_market_total_matched']:.0f}",
                "detail": "Rejects thin markets before looking at runners.",
            },
            {
                "label": "Best back size",
                "value": f">= {definition['min_best_back_size']:.0f}",
                "detail": "Rejects runners without enough visible back size.",
            },
            {
                "label": "Stake",
                "value": f"£{definition['fixed_stake']:.2f}",
                "detail": "Paper fill stake per accepted runner.",
            },
            {
                "label": "Promotion gate",
                "value": f"{definition['acceptance_min_trades']} closed / {definition['acceptance_min_roi']:.0%} ROI",
                "detail": "Evidence threshold before considering any manual-assisted live step.",
            },
        ],
        "recent_snapshot_collections": recent_snapshot_collections(store=store),
    }


def dashboard_health(store: DashboardStore | None = None, validate_betfair: bool = True) -> dict[str, Any]:
    store = store or DashboardStore()
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
        "data_quality": _snapshot_data_quality(),
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


def open_positions(store: DashboardStore | None = None, limit: int | None = None) -> list[dict[str, Any]]:
    return dashboard_summary(store=store, open_limit=limit)["open_positions"]


def closed_positions(store: DashboardStore | None = None, limit: int | None = None) -> list[dict[str, Any]]:
    return dashboard_summary(store=store, closed_limit=limit)["closed_positions"]


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
            "data_quality": _snapshot_data_quality(path),
            "markets": [],
        }

    df = pd.read_parquet(path)
    if df.empty:
        return {
            "snapshot_path": str(path),
            "captured_at": None,
            "market_count": 0,
            "selection_count": 0,
            "data_quality": _snapshot_data_quality(path),
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
        "data_quality": _snapshot_data_quality(path),
        "markets": _records(rows),
    }


def live_odds(category: str = "tennis", max_results: int = 50, limit: int = 300) -> dict[str, Any]:
    adapter = BetfairAdapter()
    validation = adapter.validate_credentials()
    validation_payload = {
        "exchange": validation.exchange,
        "ok": validation.ok,
        "approval_status": validation.approval_status,
        "message": validation.message,
    }

    fetched_at = datetime.now(timezone.utc)
    if not validation.ok:
        return {
            "mode": "live",
            "read_only": True,
            "fetched_at": fetched_at.isoformat(),
            "category": category,
            "max_results": max_results,
            "betfair": validation_payload,
            "market_count": 0,
            "selection_count": 0,
            "data_quality": _data_quality_from_frame(pd.DataFrame()),
            "markets": [],
            "error": "Betfair validation failed.",
            "live_execution_available": False,
        }

    try:
        snapshots = adapter.list_markets(category=category, max_results=max_results)
    except Exception as exc:  # noqa: BLE001
        return {
            "mode": "live",
            "read_only": True,
            "fetched_at": fetched_at.isoformat(),
            "category": category,
            "max_results": max_results,
            "betfair": validation_payload,
            "market_count": 0,
            "selection_count": 0,
            "data_quality": _data_quality_from_frame(pd.DataFrame()),
            "markets": [],
            "error": _safe_error_message(exc),
            "live_execution_available": False,
        }

    for snapshot in snapshots:
        snapshot.captured_at = snapshot.captured_at or fetched_at
        for selection in snapshot.selections:
            selection.captured_at = selection.captured_at or snapshot.captured_at

    df = _market_rows_from_snapshots(snapshots)
    if not df.empty:
        sort_columns = [column for column in ["event_start", "market_id", "selection_name"] if column in df.columns]
        df = df.sort_values(sort_columns).head(limit).copy() if sort_columns else df.head(limit).copy()

    return {
        "mode": "live",
        "read_only": True,
        "fetched_at": fetched_at.isoformat(),
        "category": category,
        "max_results": max_results,
        "betfair": validation_payload,
        "market_count": len(snapshots),
        "selection_count": int(sum(len(snapshot.selections) for snapshot in snapshots)),
        "data_quality": _data_quality_from_frame(df),
        "markets": _records(df),
        "error": None,
        "live_execution_available": False,
    }


def run_paper_session(category: str = "tennis", max_results: int = 100) -> dict[str, Any]:
    started_at = datetime.now(timezone.utc)
    if os.getenv(LIVE_ENABLED_ENV_VAR, "false").lower() in {"true", "1", "yes"}:
        return {
            "status": "rejected",
            "started_at": started_at.isoformat(),
            "finished_at": datetime.now(timezone.utc).isoformat(),
            "category": category,
            "max_results": max_results,
            "returncode": None,
            "stdout": "",
            "stderr": "RORY_TRADER_LIVE_ENABLED is true; paper sessions require live execution disabled.",
            "summary": {},
            "live_execution_available": False,
        }

    script_path = REPO_ROOT / "scripts" / "run-paper-session.sh"
    timeout_seconds = int(os.getenv(PAPER_SESSION_TIMEOUT_ENV_VAR, str(DEFAULT_PAPER_SESSION_TIMEOUT_SECONDS)))
    env = os.environ.copy()
    env["RORY_TRADER_LIVE_ENABLED"] = "false"

    try:
        result = subprocess.run(
            [str(script_path), category, str(max_results)],
            cwd=REPO_ROOT,
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
        stdout = result.stdout
        stderr = result.stderr
        returncode = result.returncode
        status = "completed" if returncode == 0 else "failed"
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout or ""
        stderr = exc.stderr or ""
        returncode = None
        status = "timeout"

    if isinstance(stdout, bytes):
        stdout = stdout.decode("utf-8", errors="replace")
    if isinstance(stderr, bytes):
        stderr = stderr.decode("utf-8", errors="replace")

    finished_at = datetime.now(timezone.utc)
    return {
        "status": status,
        "started_at": started_at.isoformat(),
        "finished_at": finished_at.isoformat(),
        "category": category,
        "max_results": max_results,
        "returncode": returncode,
        "stdout": _truncate_text(stdout),
        "stderr": _truncate_text(stderr),
        "summary": _paper_session_summary(stdout),
        "live_execution_available": False,
    }


def _paper_session_summary(stdout: str) -> dict[str, Any]:
    keys = [
        "snapshot_path",
        "snapshots_collected",
        "strategy",
        "strategy_focus",
        "strategy_decisions",
        "strategy_acceptances",
        "strategy_rejections",
        "top_rejections",
        "proposals_created",
        "duplicate_proposals_skipped",
        "paper_fills_created",
        "journal_path",
    ]
    summary: dict[str, Any] = {}
    for key in keys:
        match = re.search(rf"^{re.escape(key)}:\s*(.+)$", stdout, flags=re.MULTILINE)
        if not match:
            continue
        raw = match.group(1).strip()
        summary[key] = int(raw) if raw.isdigit() else raw
    return summary


def _truncate_text(value: str, limit: int = 8000) -> str:
    if len(value) <= limit:
        return value
    return value[:limit] + "\n...[truncated]"


def pnl_series(store: DashboardStore | None = None, limit: int | None = None) -> dict[str, Any]:
    store = store or DashboardStore()
    realized = 0.0
    stake = 0.0
    points: list[dict[str, Any]] | deque[dict[str, Any]]
    points = deque(maxlen=limit) if limit is not None else []

    for row in _iter_journal_events(store.journal_path, {"execution", "resolution"}):
        event_type = row.get("event_type")
        payload = row.get("payload", {})
        if not isinstance(payload, dict):
            continue

        if event_type == "execution" and payload.get("accepted") is True:
            filled_stake = _float_or_none(payload.get("stake"))
            if filled_stake is None:
                continue
            stake += filled_stake
        elif event_type == "resolution":
            realized_pnl = _float_or_none(payload.get("realized_pnl"))
            if realized_pnl is None:
                continue
            realized += realized_pnl
        else:
            continue

        points.append(
            {
                "recorded_at": row.get("recorded_at"),
                "event_type": event_type,
                "cumulative_realized_pnl": round(realized, 4),
                "cumulative_stake": round(stake, 4),
            }
        )

    return {"points": list(points)}


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
