from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class SelectionSnapshot:
    exchange: str
    market_id: str
    selection_id: str
    market_title: str
    selection_name: str
    category: str
    subcategory: str
    event_start: datetime | None
    best_back: float | None
    best_lay: float | None
    last_traded: float | None
    status: str
    event_name: str | None = None
    competition_name: str | None = None
    captured_at: datetime | None = None
    raw_payload: dict = field(default_factory=dict)

    @property
    def implied_probability(self) -> float | None:
        if self.last_traded and self.last_traded > 0:
            return 1 / self.last_traded
        if self.best_back and self.best_back > 0:
            return 1 / self.best_back
        return None


@dataclass
class MarketSnapshot:
    exchange: str
    market_id: str
    market_title: str
    category: str
    subcategory: str
    event_start: datetime | None
    status: str
    selections: list[SelectionSnapshot]
    event_name: str | None = None
    competition_name: str | None = None
    captured_at: datetime | None = None
    raw_payload: dict = field(default_factory=dict)


@dataclass
class OrderIntent:
    exchange: str
    market_id: str
    selection_id: str
    side: str
    stake: float
    requested_price: float | None = None
    paper_only: bool = True
    reason: str = ""


@dataclass
class OrderQuote:
    exchange: str
    market_id: str
    selection_id: str
    side: str
    stake: float
    estimated_price: float | None
    paper_only: bool
    message: str
    raw_payload: dict = field(default_factory=dict)


@dataclass
class PaperFill:
    market_id: str
    selection_id: str
    side: str
    stake: float
    fill_price: float
    commission_paid: float
    slippage_paid: float
    timestamp: datetime


@dataclass
class ExecutionReport:
    accepted: bool
    exchange: str
    mode: str
    message: str
    fill: PaperFill | None = None


@dataclass
class Position:
    market_id: str
    selection_id: str
    side: str
    total_stake: float
    average_price: float
    realized_pnl: float = 0.0


@dataclass
class StrategySignal:
    strategy_name: str
    strategy_version: str
    market_id: str
    selection_id: str
    side: str
    confidence: float
    reason: str
    stake: float = 0.0
    requested_price: float | None = None
    snapshot_timestamp: datetime | None = None
    event_start: datetime | None = None
    holding_period_hours: float = 0.0
    tags: list[str] = field(default_factory=list)
