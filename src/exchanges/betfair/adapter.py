from __future__ import annotations

import os
from datetime import datetime
from typing import Optional

import httpx

from src.common.client import retry_request
from src.exchanges.common.adapter import ExchangeAdapter, ValidationResult
from src.exchanges.common.models import MarketSnapshot, OrderIntent, OrderQuote, SelectionSnapshot


class BetfairAdapter(ExchangeAdapter):
    name = "betfair"
    supports_live_execution = False

    def __init__(self):
        self.username = os.getenv("BETFAIR_USERNAME", "")
        self.password = os.getenv("BETFAIR_PASSWORD", "")
        self.app_key = os.getenv("BETFAIR_APP_KEY", "")
        self.cert_file = os.getenv("BETFAIR_CERT_FILE", "")
        self.key_file = os.getenv("BETFAIR_KEY_FILE", "")
        self.identity_url = "https://identitysso-cert.betfair.com/api/certlogin"
        self.api_url = "https://api.betfair.com/exchange/betting/json-rpc/v1"

    def _missing_fields(self) -> list[str]:
        missing = []
        for field_name, value in [
            ("BETFAIR_USERNAME", self.username),
            ("BETFAIR_PASSWORD", self.password),
            ("BETFAIR_APP_KEY", self.app_key),
            ("BETFAIR_CERT_FILE", self.cert_file),
            ("BETFAIR_KEY_FILE", self.key_file),
        ]:
            if not value:
                missing.append(field_name)
        return missing

    @retry_request()
    def _cert_login(self) -> dict:
        with httpx.Client(timeout=20.0, cert=(self.cert_file, self.key_file)) as client:
            response = client.post(
                self.identity_url,
                headers={"X-Application": self.app_key},
                data={"username": self.username, "password": self.password},
            )
            response.raise_for_status()
            return response.json()

    def validate_credentials(self) -> ValidationResult:
        missing = self._missing_fields()
        if missing:
            return ValidationResult(
                exchange=self.name,
                ok=False,
                approval_status="missing_credentials",
                message="Betfair credentials are incomplete.",
                details={"missing": ", ".join(missing)},
            )

        if not os.path.exists(self.cert_file) or not os.path.exists(self.key_file):
            return ValidationResult(
                exchange=self.name,
                ok=False,
                approval_status="missing_cert_files",
                message="Betfair certificate files are missing on disk.",
                details={"cert_file": self.cert_file, "key_file": self.key_file},
            )

        try:
            payload = self._cert_login()
        except Exception as exc:  # noqa: BLE001
            return ValidationResult(
                exchange=self.name,
                ok=False,
                approval_status="login_failed",
                message=f"Betfair login failed: {exc.__class__.__name__}",
            )

        login_status = payload.get("loginStatus", "UNKNOWN")
        ok = login_status == "SUCCESS"
        return ValidationResult(
            exchange=self.name,
            ok=ok,
            approval_status="ready" if ok else login_status.lower(),
            message=f"Betfair login status: {login_status}",
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
            message="Betfair live execution is disabled in milestone one.",
        )

    @staticmethod
    def normalize_market(raw_market: dict, raw_book: Optional[dict] = None) -> MarketSnapshot:
        raw_book = raw_book or {}
        runners_by_id = {str(runner.get("selectionId")): runner for runner in raw_book.get("runners", [])}
        event_start = raw_market.get("marketStartTime")
        parsed_start = None
        if event_start:
            parsed_start = datetime.fromisoformat(event_start.replace("Z", "+00:00"))

        selections = []
        for runner in raw_market.get("runners", []):
            selection_id = str(runner.get("selectionId", ""))
            runner_book = runners_by_id.get(selection_id, {})
            ex = runner_book.get("ex", {})
            best_back = (ex.get("availableToBack") or [{}])[0].get("price")
            best_lay = (ex.get("availableToLay") or [{}])[0].get("price")
            last_traded = runner_book.get("lastPriceTraded")
            selections.append(
                SelectionSnapshot(
                    exchange="betfair",
                    market_id=raw_market.get("marketId", ""),
                    selection_id=selection_id,
                    market_title=raw_market.get("marketName", ""),
                    selection_name=runner.get("runnerName", selection_id),
                    category="unknown",
                    subcategory="unknown",
                    event_start=parsed_start,
                    best_back=best_back,
                    best_lay=best_lay,
                    last_traded=last_traded,
                    status=raw_market.get("description", {}).get("marketStatus", "unknown"),
                    raw_payload={"catalogue": runner, "book": runner_book},
                )
            )

        return MarketSnapshot(
            exchange="betfair",
            market_id=raw_market.get("marketId", ""),
            market_title=raw_market.get("marketName", ""),
            category="unknown",
            subcategory="unknown",
            event_start=parsed_start,
            status=raw_market.get("description", {}).get("marketStatus", "unknown"),
            selections=selections,
            raw_payload={"catalogue": raw_market, "book": raw_book},
        )
