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
from src.trading.strategy import StrategyDecision, StrategyDefinition


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
    def __init__(self, path: Path | None = None, *, recorded_at: datetime | None = None):
        self.path = Path(path) if path is not None else runtime_path("journals", "trading_journal.jsonl")
        if recorded_at is not None and recorded_at.tzinfo is None:
            recorded_at = recorded_at.replace(tzinfo=timezone.utc)
        self.recorded_at = recorded_at
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def _append(self, event_type: str, payload: dict[str, Any]) -> None:
        record = {
            "event_type": event_type,
            "recorded_at": (self.recorded_at or datetime.now(timezone.utc)).isoformat(),
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

    def record_strategy_evaluation(
        self,
        definition: StrategyDefinition,
        decisions: list[StrategyDecision],
        *,
        snapshots_seen: int,
    ) -> None:
        rejection_counts: dict[str, int] = {}
        for decision in decisions:
            if decision.accepted:
                continue
            rejection_counts[decision.reason_code] = rejection_counts.get(decision.reason_code, 0) + 1

        self._append(
            "strategy_evaluation",
            {
                "strategy_name": definition.name,
                "strategy_version": definition.version,
                "snapshots_seen": snapshots_seen,
                "decisions_count": len(decisions),
                "accepted_count": sum(1 for decision in decisions if decision.accepted),
                "rejected_count": sum(1 for decision in decisions if not decision.accepted),
                "rejection_counts": rejection_counts,
                "decisions": [asdict(decision) for decision in decisions],
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

    def record_resolution(
        self,
        proposal_id: str,
        resolved_outcome: str,
        *,
        realized_pnl: float,
        note: str = "",
        resolved_at: datetime | None = None,
        source: str = "manual",
    ) -> None:
        self._append(
            "resolution",
            {
                "proposal_id": proposal_id,
                "resolved_outcome": resolved_outcome,
                "realized_pnl": realized_pnl,
                "resolution_note": note,
                "resolution_source": source,
                "resolved_at": resolved_at or datetime.now(timezone.utc),
            },
        )


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

    for column in ("created_at", "event_start", "fill_timestamp", "recorded_at", "resolved_at"):
        if column in df.columns:
            df[column] = pd.to_datetime(df[column], utc=True, errors="coerce")
    return df


def journal_performance_summary(path: Path | None = None, snapshot_dir: Path | None = None) -> dict[str, pd.DataFrame]:
    from src.trading.accounting import journal_performance_summary as accounting_summary

    return accounting_summary(path=path, snapshot_dir=snapshot_dir)
