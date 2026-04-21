from __future__ import annotations

import os
from datetime import datetime
from typing import Optional

from src.exchanges.common.adapter import ExchangeAdapter, ValidationResult
from src.exchanges.common.models import MarketSnapshot, OrderIntent, OrderQuote, SelectionSnapshot
from src.exchanges.common.normalize import (
    infer_smarkets_category,
    normalize_status,
    smarkets_price_to_decimal,
)


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

    @staticmethod
    def normalize_market(raw_market: dict, raw_quotes: Optional[dict] = None) -> MarketSnapshot:
        """
        Normalize Smarkets market and quotes data into a MarketSnapshot.

        Args:
            raw_market: Smarkets market response (single market object with contracts)
            raw_quotes: Optional quotes response keyed by contract_id

        Returns:
            Normalized MarketSnapshot with all selections
        """
        raw_quotes = raw_quotes or {}

        # Parse event start time
        event = raw_market.get("event", {})
        event_start = event.get("start_datetime")
        parsed_start = None
        if event_start:
            parsed_start = datetime.fromisoformat(event_start.replace("Z", "+00:00"))

        # Infer category from event slug
        full_slug = event.get("full_slug", "")
        category, subcategory = infer_smarkets_category(full_slug)

        # Normalize status
        raw_status = raw_market.get("state")
        status = normalize_status(raw_status, "smarkets")

        market_id = raw_market.get("id", "")
        market_name = raw_market.get("name", "")

        selections = []
        for contract in raw_market.get("contracts", []):
            contract_id = contract.get("id", "")
            contract_quotes = raw_quotes.get(contract_id, {})
            best_prices = contract_quotes.get("best_prices", {})

            # Extract best back/lay prices (Smarkets uses basis points)
            back_prices = best_prices.get("back", [])
            lay_prices = best_prices.get("lay", [])

            best_back = None
            best_lay = None
            if back_prices:
                best_back = smarkets_price_to_decimal(back_prices[0].get("price"))
            if lay_prices:
                best_lay = smarkets_price_to_decimal(lay_prices[0].get("price"))

            last_traded = smarkets_price_to_decimal(contract_quotes.get("last_executed_price"))

            selections.append(
                SelectionSnapshot(
                    exchange="smarkets",
                    market_id=market_id,
                    selection_id=contract_id,
                    market_title=market_name,
                    selection_name=contract.get("name", contract_id),
                    category=category,
                    subcategory=subcategory,
                    event_start=parsed_start,
                    best_back=best_back,
                    best_lay=best_lay,
                    last_traded=last_traded,
                    status=normalize_status(contract.get("state"), "smarkets"),
                    raw_payload={"contract": contract, "quotes": contract_quotes},
                )
            )

        return MarketSnapshot(
            exchange="smarkets",
            market_id=market_id,
            market_title=market_name,
            category=category,
            subcategory=subcategory,
            event_start=parsed_start,
            status=status,
            selections=selections,
            raw_payload={"market": raw_market, "quotes": raw_quotes},
        )
