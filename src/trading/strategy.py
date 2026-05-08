from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable
from dataclasses import dataclass, field
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


@dataclass
class StrategyDecision:
    strategy_name: str
    strategy_version: str
    market_id: str
    market_title: str
    category: str
    subcategory: str
    event_start: datetime | None
    captured_at: datetime
    accepted: bool
    reason_code: str
    reason: str
    selection_id: str | None = None
    selection_name: str | None = None
    side: str = "back"
    confidence: float = 0.0
    stake: float = 0.0
    requested_price: float | None = None
    best_back: float | None = None
    best_lay: float | None = None
    last_traded: float | None = None
    spread: float | None = None
    holding_period_hours: float = 0.0
    tags: list[str] = field(default_factory=list)

    def to_signal(self) -> StrategySignal:
        if not self.accepted or self.selection_id is None:
            raise ValueError("Only accepted selection decisions can become strategy signals.")
        return StrategySignal(
            strategy_name=self.strategy_name,
            strategy_version=self.strategy_version,
            market_id=self.market_id,
            selection_id=self.selection_id,
            side=self.side,
            confidence=self.confidence,
            reason=self.reason,
            stake=self.stake,
            requested_price=self.requested_price,
            snapshot_timestamp=self.captured_at,
            event_start=self.event_start,
            holding_period_hours=self.holding_period_hours,
            tags=self.tags,
        )


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
        return self.signals_from_decisions(self.evaluate_decisions(snapshots))

    @staticmethod
    def signals_from_decisions(decisions: Iterable[StrategyDecision]) -> list[StrategySignal]:
        return [decision.to_signal() for decision in decisions if decision.accepted and decision.selection_id]

    def evaluate_decisions(self, snapshots: Iterable[MarketSnapshot]) -> list[StrategyDecision]:
        now = datetime.now(timezone.utc)
        decisions: list[StrategyDecision] = []

        def market_decision(snapshot: MarketSnapshot, reason_code: str, reason: str) -> StrategyDecision:
            return StrategyDecision(
                strategy_name=self.definition.name,
                strategy_version=self.definition.version,
                market_id=snapshot.market_id,
                market_title=snapshot.market_title,
                category=snapshot.category,
                subcategory=snapshot.subcategory,
                event_start=snapshot.event_start,
                captured_at=snapshot.captured_at or now,
                accepted=False,
                reason_code=reason_code,
                reason=reason,
                holding_period_hours=self.definition.holding_period_hours,
                tags=list(self.definition.tags),
            )

        def selection_decision(
            snapshot: MarketSnapshot,
            selection,
            *,
            accepted: bool,
            reason_code: str,
            reason: str,
            confidence: float = 0.0,
        ) -> StrategyDecision:
            spread = (
                round(selection.best_lay - selection.best_back, 4)
                if selection.best_back is not None and selection.best_lay is not None
                else None
            )
            return StrategyDecision(
                strategy_name=self.definition.name,
                strategy_version=self.definition.version,
                market_id=selection.market_id,
                market_title=selection.market_title or snapshot.market_title,
                category=selection.category,
                subcategory=selection.subcategory,
                event_start=selection.event_start or snapshot.event_start,
                captured_at=selection.captured_at or snapshot.captured_at or now,
                accepted=accepted,
                reason_code=reason_code,
                reason=reason,
                selection_id=selection.selection_id,
                selection_name=selection.selection_name,
                side="back",
                confidence=round(confidence, 3),
                stake=self.definition.fixed_stake if accepted else 0.0,
                requested_price=selection.best_back if accepted else None,
                best_back=selection.best_back,
                best_lay=selection.best_lay,
                last_traded=selection.last_traded,
                spread=spread,
                holding_period_hours=self.definition.holding_period_hours,
                tags=list(self.definition.tags),
            )

        for snapshot in snapshots:
            if snapshot.category not in self.definition.allowed_categories:
                decisions.append(
                    market_decision(
                        snapshot,
                        "market_category_not_allowed",
                        f"Category {snapshot.category} is outside allowed categories.",
                    )
                )
                continue
            if snapshot.status != "open":
                decisions.append(
                    market_decision(
                        snapshot,
                        "market_not_open",
                        f"Market status is {snapshot.status}, not open.",
                    )
                )
                continue
            if snapshot.event_start is None:
                decisions.append(
                    market_decision(
                        snapshot,
                        "event_start_missing",
                        "Market has no event start time.",
                    )
                )
                continue

            hours_to_event = (snapshot.event_start - now).total_seconds() / 3600
            if hours_to_event < self.definition.min_hours_to_event:
                decisions.append(
                    market_decision(
                        snapshot,
                        "event_start_too_soon",
                        f"Event starts in {hours_to_event:.1f}h; minimum is {self.definition.min_hours_to_event:.1f}h.",
                    )
                )
                continue
            if hours_to_event > self.definition.max_hours_to_event:
                decisions.append(
                    market_decision(
                        snapshot,
                        "event_start_too_far",
                        f"Event starts in {hours_to_event:.1f}h; maximum is {self.definition.max_hours_to_event:.1f}h.",
                    )
                )
                continue
            if self.definition.allowed_subcategories and snapshot.subcategory not in self.definition.allowed_subcategories:
                decisions.append(
                    market_decision(
                        snapshot,
                        "subcategory_not_allowed",
                        f"Subcategory {snapshot.subcategory} is outside allowed subcategories.",
                    )
                )
                continue

            for selection in snapshot.selections:
                if selection.status != "open":
                    decisions.append(
                        selection_decision(
                            snapshot,
                            selection,
                            accepted=False,
                            reason_code="selection_not_open",
                            reason=f"Selection status is {selection.status}, not open.",
                        )
                    )
                    continue
                if selection.best_back is None or selection.best_lay is None:
                    decisions.append(
                        selection_decision(
                            snapshot,
                            selection,
                            accepted=False,
                            reason_code="missing_back_or_lay",
                            reason="Selection is missing best back or best lay price.",
                        )
                    )
                    continue
                if selection.best_back < self.definition.min_back_price:
                    decisions.append(
                        selection_decision(
                            snapshot,
                            selection,
                            accepted=False,
                            reason_code="back_price_below_min",
                            reason=(
                                f"Best back {selection.best_back:.2f} is below minimum "
                                f"{self.definition.min_back_price:.2f}."
                            ),
                        )
                    )
                    continue
                if selection.best_back > self.definition.max_back_price:
                    decisions.append(
                        selection_decision(
                            snapshot,
                            selection,
                            accepted=False,
                            reason_code="back_price_above_max",
                            reason=(
                                f"Best back {selection.best_back:.2f} is above maximum "
                                f"{self.definition.max_back_price:.2f}."
                            ),
                        )
                    )
                    continue

                spread = selection.best_lay - selection.best_back
                if spread > self.definition.max_spread:
                    decisions.append(
                        selection_decision(
                            snapshot,
                            selection,
                            accepted=False,
                            reason_code="spread_too_wide",
                            reason=f"Spread {spread:.2f} is wider than maximum {self.definition.max_spread:.2f}.",
                        )
                    )
                    continue

                confidence = max(0.0, min(1.0, 1.0 - (spread / max(self.definition.max_spread, 0.01))))
                reason = (
                    f"Eligible pre-match sports runner in target price bucket "
                    f"({selection.best_back:.2f}) with spread {spread:.2f} "
                    f"{hours_to_event:.1f}h before event start."
                )
                decisions.append(
                    selection_decision(
                        snapshot,
                        selection,
                        accepted=True,
                        reason_code="accepted",
                        reason=reason,
                        confidence=confidence,
                    )
                )

        return decisions
