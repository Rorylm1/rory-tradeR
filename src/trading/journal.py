from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from src.common.paths import runtime_path
from src.exchanges.common.models import ExecutionReport, MarketSnapshot, StrategySignal


@dataclass
class ProposedTrade:
    proposal_id: str
    created_at: datetime
    strategy_name: str
    strategy_version: str
    exchange: str
    market_id: str
    selection_id: str
    market_title: str
    selection_name: str
    category: str
    subcategory: str
    event_start: datetime | None
    event_name: str | None
    competition_name: str | None
    side: str
    stake: float
    requested_price: float | None
    best_back: float | None
    best_lay: float | None
    last_traded: float | None
    signal_confidence: float
    reason: str
    holding_period_hours: float
    status: str = "proposed"


class JournalStore:
    def __init__(self, path: Path | None = None):
        self.path = Path(path) if path is not None else runtime_path("journals", "trading_journal.jsonl")
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def _append(self, event_type: str, payload: dict[str, Any]) -> None:
        record = {
            "event_type": event_type,
            "recorded_at": datetime.now(timezone.utc).isoformat(),
            "payload": self._json_safe(payload),
        }
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True) + "\n")

    @staticmethod
    def _json_safe(payload: dict[str, Any]) -> dict[str, Any]:
        def convert(value: Any) -> Any:
            if isinstance(value, datetime):
                return value.isoformat()
            if isinstance(value, dict):
                return {k: convert(v) for k, v in value.items()}
            if isinstance(value, list):
                return [convert(v) for v in value]
            return value

        return {key: convert(value) for key, value in payload.items()}

    @staticmethod
    def build_proposal_id(signal: StrategySignal) -> str:
        raw = "|".join(
            [
                signal.strategy_name,
                signal.strategy_version,
                signal.market_id,
                signal.selection_id,
                signal.side,
                signal.snapshot_timestamp.isoformat() if signal.snapshot_timestamp else "",
            ]
        )
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]

    def load_events(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        rows: list[dict[str, Any]] = []
        with self.path.open(encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    rows.append(json.loads(line))
        return rows

    def has_proposal(self, proposal_id: str) -> bool:
        for event in self.load_events():
            if event["event_type"] == "proposal" and event["payload"].get("proposal_id") == proposal_id:
                return True
        return False

    def record_snapshot_collection(self, snapshot_path: Path, snapshot_count: int, category: str | None) -> None:
        self._append(
            "snapshot_collection",
            {
                "snapshot_path": str(snapshot_path),
                "snapshot_count": snapshot_count,
                "category": category or "all",
            },
        )

    def record_proposal(self, signal: StrategySignal, snapshot: MarketSnapshot) -> ProposedTrade | None:
        proposal_id = self.build_proposal_id(signal)
        if self.has_proposal(proposal_id):
            return None

        selection = next((item for item in snapshot.selections if item.selection_id == signal.selection_id), None)
        if selection is None:
            raise ValueError(f"Selection {signal.selection_id} not found in snapshot {snapshot.market_id}")

        proposal = ProposedTrade(
            proposal_id=proposal_id,
            created_at=signal.snapshot_timestamp or datetime.now(timezone.utc),
            strategy_name=signal.strategy_name,
            strategy_version=signal.strategy_version,
            exchange=snapshot.exchange,
            market_id=snapshot.market_id,
            selection_id=selection.selection_id,
            market_title=snapshot.market_title,
            selection_name=selection.selection_name,
            category=selection.category,
            subcategory=selection.subcategory,
            event_start=selection.event_start,
            event_name=selection.event_name or snapshot.event_name,
            competition_name=selection.competition_name or snapshot.competition_name,
            side=signal.side,
            stake=signal.stake,
            requested_price=signal.requested_price,
            best_back=selection.best_back,
            best_lay=selection.best_lay,
            last_traded=selection.last_traded,
            signal_confidence=signal.confidence,
            reason=signal.reason,
            holding_period_hours=signal.holding_period_hours,
        )
        payload = asdict(proposal)
        self._append("proposal", payload)
        return proposal

    def record_live_review(self, proposal_id: str, status: str, note: str = "") -> None:
        self._append(
            "live_review",
            {
                "proposal_id": proposal_id,
                "status": status,
                "note": note,
            },
        )

    def record_execution(
        self,
        proposal_id: str,
        report: ExecutionReport,
        *,
        mode: str,
        resolved_outcome: str | None = None,
        realized_pnl: float | None = None,
    ) -> None:
        payload: dict[str, Any] = {
            "proposal_id": proposal_id,
            "mode": mode,
            "accepted": report.accepted,
            "exchange": report.exchange,
            "message": report.message,
            "resolved_outcome": resolved_outcome,
            "realized_pnl": realized_pnl,
        }
        if report.fill is not None:
            payload.update(
                {
                    "fill_price": report.fill.fill_price,
                    "commission_paid": report.fill.commission_paid,
                    "slippage_paid": report.fill.slippage_paid,
                    "fill_timestamp": report.fill.timestamp,
                    "stake": report.fill.stake,
                    "side": report.fill.side,
                }
            )
        self._append("execution", payload)


def journal_dataframe(path: Path | None = None) -> pd.DataFrame:
    store = JournalStore(path=path)
    events = store.load_events()
    if not events:
        return pd.DataFrame()

    records: list[dict[str, Any]] = []
    for event in events:
        row = {"event_type": event["event_type"], "recorded_at": event["recorded_at"]}
        row.update(event["payload"])
        records.append(row)
    df = pd.DataFrame(records)

    for column in ("created_at", "event_start", "fill_timestamp", "recorded_at"):
        if column in df.columns:
            df[column] = pd.to_datetime(df[column], utc=True, errors="coerce")
    return df


def journal_performance_summary(path: Path | None = None) -> dict[str, pd.DataFrame]:
    df = journal_dataframe(path=path)
    if df.empty:
        empty = pd.DataFrame()
        return {"events": df, "strategy": empty, "price_bucket": empty, "time_window": empty}

    proposals = df[df["event_type"] == "proposal"].copy()
    executions = df[df["event_type"] == "execution"].copy()

    merged = proposals.merge(executions, on="proposal_id", how="left", suffixes=("_proposal", "_execution"))
    if merged.empty:
        empty = pd.DataFrame()
        return {"events": df, "strategy": empty, "price_bucket": empty, "time_window": empty}

    requested_price_column = "requested_price_proposal" if "requested_price_proposal" in merged.columns else "requested_price"
    created_at_column = "created_at_proposal" if "created_at_proposal" in merged.columns else "created_at"
    event_start_column = "event_start_proposal" if "event_start_proposal" in merged.columns else "event_start"
    strategy_name_column = "strategy_name_proposal" if "strategy_name_proposal" in merged.columns else "strategy_name"
    strategy_version_column = (
        "strategy_version_proposal" if "strategy_version_proposal" in merged.columns else "strategy_version"
    )
    confidence_column = "signal_confidence_proposal" if "signal_confidence_proposal" in merged.columns else "signal_confidence"
    stake_column = "stake_proposal" if "stake_proposal" in merged.columns else "stake"
    commission_column = "commission_paid_execution" if "commission_paid_execution" in merged.columns else "commission_paid"
    slippage_column = "slippage_paid_execution" if "slippage_paid_execution" in merged.columns else "slippage_paid"
    accepted_column = "accepted_execution" if "accepted_execution" in merged.columns else "accepted"
    commission = merged[commission_column] if commission_column in merged.columns else pd.Series(0.0, index=merged.index)
    slippage = merged[slippage_column] if slippage_column in merged.columns else pd.Series(0.0, index=merged.index)
    accepted = (
        merged[accepted_column].astype("boolean")
        if accepted_column in merged.columns
        else pd.Series(False, index=merged.index, dtype="boolean")
    )
    merged["net_cost"] = commission.fillna(0) + slippage.fillna(0)
    merged["accepted"] = accepted.fillna(False).astype(bool)
    merged["price_bucket"] = pd.cut(
        merged[requested_price_column],
        bins=[0, 1.5, 2.0, 3.0, 5.0, 10.0, 100.0],
        labels=["<=1.5", "1.5-2.0", "2.0-3.0", "3.0-5.0", "5.0-10.0", "10.0+"],
        include_lowest=True,
    )
    merged["hours_to_event"] = (
        (merged[event_start_column] - merged[created_at_column]).dt.total_seconds() / 3600
        if event_start_column in merged.columns and created_at_column in merged.columns
        else pd.Series(dtype=float)
    )
    merged["time_window"] = pd.cut(
        merged["hours_to_event"],
        bins=[0, 6, 12, 24, 48, 96, 999999],
        labels=["0-6h", "6-12h", "12-24h", "24-48h", "48-96h", "96h+"],
        include_lowest=True,
    )

    strategy = (
        merged.groupby([strategy_name_column, strategy_version_column], dropna=False)
        .agg(
            proposals=("proposal_id", "count"),
            accepted_trades=("accepted", "sum"),
            avg_confidence=(confidence_column, "mean"),
            total_stake=(stake_column, "sum"),
            total_cost=("net_cost", "sum"),
        )
        .reset_index()
    )
    strategy = strategy.rename(
        columns={
            strategy_name_column: "strategy_name",
            strategy_version_column: "strategy_version",
        }
    )

    price_bucket = (
        merged.groupby(["price_bucket"], dropna=False, observed=False)
        .agg(
            proposals=("proposal_id", "count"),
            accepted_trades=("accepted", "sum"),
            avg_confidence=(confidence_column, "mean"),
            total_cost=("net_cost", "sum"),
        )
        .reset_index()
    )

    time_window = (
        merged.groupby(["time_window"], dropna=False, observed=False)
        .agg(
            proposals=("proposal_id", "count"),
            accepted_trades=("accepted", "sum"),
            avg_confidence=(confidence_column, "mean"),
            total_cost=("net_cost", "sum"),
        )
        .reset_index()
    )

    return {
        "events": df,
        "merged": merged,
        "strategy": strategy,
        "price_bucket": price_bucket,
        "time_window": time_window,
    }
