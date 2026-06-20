from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.exchanges.common.models import ExecutionReport, MarketSnapshot, OrderIntent, PaperFill


@dataclass
class BrokerConfig:
    commission_rate: float = 0.02
    slippage_bps: float = 25.0
    max_stake_per_trade: float = 10.0
    max_market_exposure: float = 20.0
    max_daily_loss: float = 20.0
    max_snapshot_age_seconds: int = 30 * 60
    min_available_size: float = 2.0

    @classmethod
    def from_env(cls) -> BrokerConfig:
        return cls(
            commission_rate=_env_float("RORY_TRADER_PAPER_COMMISSION_RATE", cls.commission_rate),
            slippage_bps=_env_float("RORY_TRADER_PAPER_SLIPPAGE_BPS", cls.slippage_bps),
            max_stake_per_trade=_env_float("RORY_TRADER_MAX_STAKE_PER_TRADE", cls.max_stake_per_trade),
            max_market_exposure=_env_float("RORY_TRADER_MAX_MARKET_EXPOSURE", cls.max_market_exposure),
            max_daily_loss=_env_float("RORY_TRADER_MAX_DAILY_LOSS", cls.max_daily_loss),
            max_snapshot_age_seconds=int(
                _env_float("RORY_TRADER_PAPER_MAX_SNAPSHOT_AGE_SECONDS", cls.max_snapshot_age_seconds)
            ),
            min_available_size=_env_float("RORY_TRADER_PAPER_MIN_AVAILABLE_SIZE", cls.min_available_size),
        )


class PaperBroker:
    def __init__(
        self,
        config: BrokerConfig | None = None,
        *,
        journal_path: Path | None = None,
        snapshot_dir: Path | None = None,
    ):
        self.config = config or BrokerConfig.from_env()
        self.journal_path = journal_path
        self.snapshot_dir = snapshot_dir

    def execute(
        self,
        order_intent: OrderIntent,
        market_snapshot: MarketSnapshot,
        *,
        now: datetime | None = None,
    ) -> ExecutionReport:
        now = now or datetime.now(timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)
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
        intent_exposure = self._intent_exposure(order_intent, fill_price)
        portfolio_state = self._portfolio_state(now)
        if portfolio_state is None:
            return ExecutionReport(
                accepted=False,
                exchange=order_intent.exchange,
                mode="paper",
                message="Portfolio risk state is unavailable; refusing paper fill.",
            )

        current_market_exposure = portfolio_state["market_exposure"].get(order_intent.market_id, 0.0)
        projected_market_exposure = current_market_exposure + intent_exposure
        if projected_market_exposure > self.config.max_market_exposure:
            return ExecutionReport(
                accepted=False,
                exchange=order_intent.exchange,
                mode="paper",
                message="Projected market exposure exceeds max_market_exposure.",
            )

        daily_realized_pnl = portfolio_state["daily_realized_pnl"]
        if daily_realized_pnl <= -self.config.max_daily_loss:
            return ExecutionReport(
                accepted=False,
                exchange=order_intent.exchange,
                mode="paper",
                message="Daily realized loss has reached max_daily_loss.",
            )
        if daily_realized_pnl - intent_exposure < -self.config.max_daily_loss:
            return ExecutionReport(
                accepted=False,
                exchange=order_intent.exchange,
                mode="paper",
                message="Worst-case loss would exceed max_daily_loss.",
            )

        commission_paid = order_intent.stake * self.config.commission_rate

        fill = PaperFill(
            market_id=order_intent.market_id,
            selection_id=order_intent.selection_id,
            side=order_intent.side,
            stake=order_intent.stake,
            fill_price=round(fill_price, 4),
            commission_paid=round(commission_paid, 4),
            slippage_paid=round(slippage, 4),
            timestamp=now,
        )

        return ExecutionReport(
            accepted=True,
            exchange=order_intent.exchange,
            mode="paper",
            message="Paper fill created successfully.",
            fill=fill,
        )

    def _portfolio_state(self, now: datetime) -> dict[str, Any] | None:
        try:
            import pandas as pd

            from src.trading.accounting import journal_performance_summary
        except Exception:  # noqa: BLE001
            return None

        try:
            summary = journal_performance_summary(path=self.journal_path, snapshot_dir=self.snapshot_dir)
        except Exception:  # noqa: BLE001
            return None

        market_exposure: dict[str, float] = {}
        open_positions = summary["open_positions"]
        if not open_positions.empty:
            for _, row in open_positions.iterrows():
                market_id = str(row.get("market_id", ""))
                exposure = self._position_exposure(row)
                market_exposure[market_id] = market_exposure.get(market_id, 0.0) + exposure

        daily_realized_pnl = 0.0
        closed_positions = summary["closed_positions"]
        if not closed_positions.empty and "resolved_at" in closed_positions.columns:
            for _, row in closed_positions.iterrows():
                resolved_at = row.get("resolved_at")
                realized_pnl = row.get("realized_pnl")
                if resolved_at is None or realized_pnl is None or pd.isna(resolved_at) or pd.isna(realized_pnl):
                    continue
                if hasattr(resolved_at, "to_pydatetime"):
                    resolved_at = resolved_at.to_pydatetime()
                if resolved_at.tzinfo is None:
                    resolved_at = resolved_at.replace(tzinfo=timezone.utc)
                if resolved_at.date() == now.date():
                    daily_realized_pnl += float(realized_pnl)

        return {
            "market_exposure": {market_id: round(value, 4) for market_id, value in market_exposure.items()},
            "daily_realized_pnl": round(daily_realized_pnl, 4),
        }

    @staticmethod
    def _intent_exposure(order_intent: OrderIntent, fill_price: float) -> float:
        if order_intent.side == "lay":
            return round(order_intent.stake * max(fill_price - 1.0, 0.0), 4)
        return round(order_intent.stake, 4)

    @staticmethod
    def _position_exposure(row: Any) -> float:
        stake = float(row.get("stake", 0.0) or 0.0)
        side = str(row.get("side", "back"))
        if side == "lay":
            fill_price = float(row.get("fill_price", 1.0) or 1.0)
            return round(stake * max(fill_price - 1.0, 0.0), 4)
        return round(stake, 4)


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    try:
        return float(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be numeric.") from exc
