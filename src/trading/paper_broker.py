from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from src.exchanges.common.models import ExecutionReport, MarketSnapshot, OrderIntent, PaperFill


@dataclass
class BrokerConfig:
    commission_rate: float = 0.02
    slippage_bps: float = 25.0
    max_stake_per_trade: float = 100.0
    max_snapshot_age_seconds: int = 30 * 60
    min_available_size: float = 2.0


class PaperBroker:
    def __init__(self, config: BrokerConfig | None = None):
        self.config = config or BrokerConfig()

    def execute(self, order_intent: OrderIntent, market_snapshot: MarketSnapshot) -> ExecutionReport:
        now = datetime.now(timezone.utc)
        captured_at = market_snapshot.captured_at
        if captured_at is None:
            return ExecutionReport(
                accepted=False,
                exchange=order_intent.exchange,
                mode="paper",
                message="Market snapshot has no capture timestamp; refusing stale-unknown paper fill.",
            )
        if captured_at.tzinfo is None:
            captured_at = captured_at.replace(tzinfo=timezone.utc)
        snapshot_age_seconds = (now - captured_at).total_seconds()
        if snapshot_age_seconds > self.config.max_snapshot_age_seconds:
            return ExecutionReport(
                accepted=False,
                exchange=order_intent.exchange,
                mode="paper",
                message="Market snapshot is stale; refusing paper fill.",
            )

        if not order_intent.paper_only:
            return ExecutionReport(
                accepted=False,
                exchange=order_intent.exchange,
                mode="paper",
                message="Paper broker rejects non-paper intents.",
            )

        if order_intent.stake > self.config.max_stake_per_trade:
            return ExecutionReport(
                accepted=False,
                exchange=order_intent.exchange,
                mode="paper",
                message="Stake exceeds max_stake_per_trade.",
            )

        selection = next(
            (item for item in market_snapshot.selections if item.selection_id == order_intent.selection_id),
            None,
        )
        if selection is None:
            return ExecutionReport(
                accepted=False,
                exchange=order_intent.exchange,
                mode="paper",
                message="Selection not found in market snapshot.",
            )

        base_price = selection.best_back if order_intent.side == "back" else selection.best_lay
        if base_price is None:
            return ExecutionReport(
                accepted=False,
                exchange=order_intent.exchange,
                mode="paper",
                message="No executable paper price available for selection.",
            )
        available_size = selection.best_back_size if order_intent.side == "back" else selection.best_lay_size
        if available_size is not None and available_size < self.config.min_available_size:
            return ExecutionReport(
                accepted=False,
                exchange=order_intent.exchange,
                mode="paper",
                message="Available exchange size is below min_available_size.",
            )

        slippage = base_price * (self.config.slippage_bps / 10000)
        fill_price = base_price + slippage if order_intent.side == "back" else max(base_price - slippage, 1.01)
        commission_paid = order_intent.stake * self.config.commission_rate

        fill = PaperFill(
            market_id=order_intent.market_id,
            selection_id=order_intent.selection_id,
            side=order_intent.side,
            stake=order_intent.stake,
            fill_price=round(fill_price, 4),
            commission_paid=round(commission_paid, 4),
            slippage_paid=round(slippage, 4),
            timestamp=datetime.now(timezone.utc),
        )

        return ExecutionReport(
            accepted=True,
            exchange=order_intent.exchange,
            mode="paper",
            message="Paper fill created successfully.",
            fill=fill,
        )
