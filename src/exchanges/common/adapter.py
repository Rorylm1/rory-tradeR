from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional

from src.exchanges.common.models import MarketSnapshot, OrderIntent, OrderQuote


@dataclass
class ValidationResult:
    exchange: str
    ok: bool
    approval_status: str
    message: str
    details: dict[str, str] = field(default_factory=dict)


class ExchangeAdapter(ABC):
    name: str
    supports_live_execution: bool = False

    @abstractmethod
    def validate_credentials(self) -> ValidationResult:
        """Validate exchange readiness without exposing secrets."""

    @abstractmethod
    def list_markets(self, category: Optional[str] = None, max_results: int = 10) -> list[MarketSnapshot]:
        """Fetch normalized market snapshots for the exchange."""

    @abstractmethod
    def build_order_quote(self, order_intent: OrderIntent) -> OrderQuote:
        """Map an order intent into an exchange-aware quote object."""
