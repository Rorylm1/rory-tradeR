from __future__ import annotations

import os
from typing import Optional

from src.exchanges.common.adapter import ExchangeAdapter, ValidationResult
from src.exchanges.common.models import MarketSnapshot, OrderIntent, OrderQuote


class SmarketsAdapter(ExchangeAdapter):
    name = "smarkets"
    supports_live_execution = False

    def __init__(self):
        self.api_token = os.getenv("SMARKETS_API_TOKEN", "")
        self.api_enabled = os.getenv("SMARKETS_API_ENABLED", "false").lower() == "true"
        self.api_base_url = os.getenv("SMARKETS_API_BASE_URL", "https://api.smarkets.com")

    def validate_credentials(self) -> ValidationResult:
        if not self.api_enabled:
            return ValidationResult(
                exchange=self.name,
                ok=False,
                approval_status="approval_required",
                message="Smarkets API is disabled until account approval is confirmed.",
            )

        if not self.api_token:
            return ValidationResult(
                exchange=self.name,
                ok=False,
                approval_status="missing_token",
                message="Smarkets API token is missing.",
            )

        return ValidationResult(
            exchange=self.name,
            ok=True,
            approval_status="ready",
            message="Smarkets API appears configured. Endpoint-level validation is still conservative.",
        )

    def list_markets(self, category: Optional[str] = None, max_results: int = 10) -> list[MarketSnapshot]:
        return []

    def build_order_quote(self, order_intent: OrderIntent) -> OrderQuote:
        return OrderQuote(
            exchange=self.name,
            market_id=order_intent.market_id,
            selection_id=order_intent.selection_id,
            side=order_intent.side,
            stake=order_intent.stake,
            estimated_price=order_intent.requested_price,
            paper_only=True,
            message="Smarkets live execution is disabled in milestone one.",
        )
