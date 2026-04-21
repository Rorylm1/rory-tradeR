from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timezone

from src.exchanges.common.models import MarketSnapshot, OrderIntent, StrategySignal


@dataclass
class StrategyDefinition:
    name: str
    version: str
    description: str
    fixed_stake: float
    min_hours_to_event: float
    max_hours_to_event: float
    min_back_price: float
    max_back_price: float
    max_spread: float
    allowed_categories: tuple[str, ...] = ("sports",)
    allowed_subcategories: tuple[str, ...] = ()
    holding_period_hours: float = 24.0
    kill_conditions: tuple[str, ...] = (
        "market_not_open",
        "event_start_too_soon",
        "spread_too_wide",
        "missing_back_or_lay",
    )
    acceptance_min_trades: int = 50
    acceptance_min_roi: float = 0.02
    tags: tuple[str, ...] = ("betfair", "pre_match", "back_only")


class Strategy(ABC):
    def __init__(self, definition: StrategyDefinition):
        self.definition = definition

    @abstractmethod
    def evaluate(self, snapshots: Iterable[MarketSnapshot]) -> list[StrategySignal]:
        """Evaluate snapshots and emit strategy signals."""

    def to_order_intent(self, signal: StrategySignal, exchange: str = "betfair") -> OrderIntent:
        return OrderIntent(
            exchange=exchange,
            market_id=signal.market_id,
            selection_id=signal.selection_id,
            side=signal.side,
            stake=signal.stake,
            requested_price=signal.requested_price,
            paper_only=True,
            reason=signal.reason,
        )


@dataclass
class BackPriceBucketConfig:
    fixed_stake: float = 2.0
    min_hours_to_event: float = 6.0
    max_hours_to_event: float = 72.0
    min_back_price: float = 1.8
    max_back_price: float = 3.6
    max_spread: float = 0.12
    allowed_subcategories: tuple[str, ...] = ()
    acceptance_min_trades: int = 50
    acceptance_min_roi: float = 0.02
    name: str = "betfair_pre_match_back_bucket"
    version: str = "v1"
    description: str = (
        "Back-only pre-match sports candidate that targets mid-priced runners in slower, tighter pre-match books."
    )
    holding_period_hours: float = 24.0
    tags: tuple[str, ...] = ("betfair", "sports", "pre_match", "back_only", "price_bucket")

    def to_definition(self) -> StrategyDefinition:
        return StrategyDefinition(
            name=self.name,
            version=self.version,
            description=self.description,
            fixed_stake=self.fixed_stake,
            min_hours_to_event=self.min_hours_to_event,
            max_hours_to_event=self.max_hours_to_event,
            min_back_price=self.min_back_price,
            max_back_price=self.max_back_price,
            max_spread=self.max_spread,
            allowed_subcategories=self.allowed_subcategories,
            holding_period_hours=self.holding_period_hours,
            acceptance_min_trades=self.acceptance_min_trades,
            acceptance_min_roi=self.acceptance_min_roi,
            tags=self.tags,
        )


class BackPriceBucketStrategy(Strategy):
    def __init__(self, config: BackPriceBucketConfig | None = None):
        self.config = config or BackPriceBucketConfig()
        super().__init__(self.config.to_definition())

    def evaluate(self, snapshots: Iterable[MarketSnapshot]) -> list[StrategySignal]:
        now = datetime.now(timezone.utc)
        signals: list[StrategySignal] = []

        for snapshot in snapshots:
            if snapshot.category not in self.definition.allowed_categories:
                continue
            if snapshot.status != "open":
                continue
            if snapshot.event_start is None:
                continue

            hours_to_event = (snapshot.event_start - now).total_seconds() / 3600
            if hours_to_event < self.definition.min_hours_to_event:
                continue
            if hours_to_event > self.definition.max_hours_to_event:
                continue
            if self.definition.allowed_subcategories and snapshot.subcategory not in self.definition.allowed_subcategories:
                continue

            for selection in snapshot.selections:
                if selection.status != "open":
                    continue
                if selection.best_back is None or selection.best_lay is None:
                    continue
                if selection.best_back < self.definition.min_back_price:
                    continue
                if selection.best_back > self.definition.max_back_price:
                    continue

                spread = selection.best_lay - selection.best_back
                if spread > self.definition.max_spread:
                    continue

                confidence = max(0.0, min(1.0, 1.0 - (spread / max(self.definition.max_spread, 0.01))))
                reason = (
                    f"Eligible pre-match sports runner in target price bucket "
                    f"({selection.best_back:.2f}) with spread {spread:.2f} "
                    f"{hours_to_event:.1f}h before event start."
                )
                signals.append(
                    StrategySignal(
                        strategy_name=self.definition.name,
                        strategy_version=self.definition.version,
                        market_id=selection.market_id,
                        selection_id=selection.selection_id,
                        side="back",
                        confidence=round(confidence, 3),
                        reason=reason,
                        stake=self.definition.fixed_stake,
                        requested_price=selection.best_back,
                        snapshot_timestamp=snapshot.captured_at or now,
                        event_start=selection.event_start,
                        holding_period_hours=self.definition.holding_period_hours,
                        tags=list(self.definition.tags),
                    )
                )

        return signals
