from __future__ import annotations

import os
from datetime import datetime, timezone

import httpx

from src.common.client import retry_request
from src.exchanges.common.adapter import ExchangeAdapter, ValidationResult
from src.exchanges.common.models import MarketSnapshot, OrderIntent, OrderQuote, SelectionSnapshot
from src.exchanges.common.normalize import BETFAIR_EVENT_TYPE_MAP, infer_betfair_category, normalize_status


class BetfairAdapter(ExchangeAdapter):
    name = "betfair"
    supports_live_execution = False

    def __init__(self):
        self.username = os.getenv("BETFAIR_USERNAME", "")
        self.password = os.getenv("BETFAIR_PASSWORD", "")
        self.app_key = os.getenv("BETFAIR_APP_KEY", "")
        self.cert_file = os.getenv("BETFAIR_CERT_FILE", "")
        self.key_file = os.getenv("BETFAIR_KEY_FILE", "")
        self.use_cert_login = os.getenv("BETFAIR_USE_CERT_LOGIN", "false").lower() == "true"
        self.cert_identity_url = "https://identitysso-cert.betfair.com/api/certlogin"
        self.interactive_identity_url = "https://identitysso.betfair.com/api/login"
        self.api_url = "https://api.betfair.com/exchange/betting/json-rpc/v1"
        self._session_token: str | None = None

    def _event_type_ids_for_category(self, category: str | None) -> list[str]:
        if not category:
            return []

        category_lower = category.strip().lower()
        matches: list[str] = []
        for event_type_id, (group, subcategory) in BETFAIR_EVENT_TYPE_MAP.items():
            if category_lower == group or category_lower == subcategory:
                matches.append(event_type_id)
        return matches

    def _market_type_codes_for_category(self, category: str | None) -> list[str]:
        if not category:
            return []

        category_lower = category.strip().lower()
        if category_lower != "tennis":
            return []

        raw = os.getenv("RORY_TRADER_BETFAIR_TENNIS_MARKET_TYPES", "MATCH_ODDS,SET_WINNER")
        return [item.strip().upper() for item in raw.split(",") if item.strip()]

    def _missing_fields(self) -> list[str]:
        missing = []
        required = [
            ("BETFAIR_USERNAME", self.username),
            ("BETFAIR_PASSWORD", self.password),
            ("BETFAIR_APP_KEY", self.app_key),
        ]
        if self.use_cert_login:
            required.extend([
                ("BETFAIR_CERT_FILE", self.cert_file),
                ("BETFAIR_KEY_FILE", self.key_file),
            ])
        for field_name, value in required:
            if not value:
                missing.append(field_name)
        return missing

    @retry_request()
    def _cert_login(self) -> dict:
        """Login using SSL client certificate (for automated/production use)."""
        with httpx.Client(timeout=20.0, cert=(self.cert_file, self.key_file)) as client:
            response = client.post(
                self.cert_identity_url,
                headers={"X-Application": self.app_key},
                data={"username": self.username, "password": self.password},
            )
            response.raise_for_status()
            return response.json()

    @retry_request()
    def _interactive_login(self) -> dict:
        """Login using username/password only (for development/testing)."""
        from urllib.parse import urlencode

        with httpx.Client(timeout=20.0, follow_redirects=True) as client:
            response = client.post(
                self.interactive_identity_url,
                headers={
                    "X-Application": self.app_key,
                    "Accept": "application/json",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                content=urlencode({"username": self.username, "password": self.password}),
            )
            response.raise_for_status()
            return response.json()

    def _login(self) -> dict:
        """Login using configured method (cert or interactive)."""
        if self.use_cert_login:
            return self._cert_login()
        return self._interactive_login()

    @retry_request()
    def _rpc_request(self, method: str, params: dict) -> dict | list:
        if not self._session_token:
            raise RuntimeError("Betfair session token is missing.")

        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "id": 1,
        }

        with httpx.Client(timeout=20.0) as client:
            response = client.post(
                self.api_url,
                headers={
                    "X-Application": self.app_key,
                    "X-Authentication": self._session_token,
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

        if isinstance(data, dict) and data.get("error"):
            raise RuntimeError(f"Betfair API error: {data['error']}")

        if isinstance(data, list):
            if data and data[0].get("error"):
                raise RuntimeError(f"Betfair API error: {data[0]['error']}")
            return data[0].get("result", []) if data else []

        return data.get("result", [])

    def _ensure_session_token(self) -> None:
        if self._session_token:
            return

        result = self.validate_credentials()
        if not result.ok or not self._session_token:
            raise RuntimeError(result.message)

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

        if self.use_cert_login:
            if not os.path.exists(self.cert_file) or not os.path.exists(self.key_file):
                return ValidationResult(
                    exchange=self.name,
                    ok=False,
                    approval_status="missing_cert_files",
                    message="Betfair certificate files are missing on disk.",
                    details={"cert_file": self.cert_file, "key_file": self.key_file},
                )

        try:
            payload = self._login()
        except Exception as exc:  # noqa: BLE001
            return ValidationResult(
                exchange=self.name,
                ok=False,
                approval_status="login_failed",
                message=f"Betfair login failed: {exc.__class__.__name__}",
            )

        login_status = payload.get("loginStatus", payload.get("status", "UNKNOWN"))
        ok = login_status == "SUCCESS"
        if ok:
            self._session_token = payload.get("sessionToken", payload.get("token"))
        login_mode = "cert" if self.use_cert_login else "interactive"
        return ValidationResult(
            exchange=self.name,
            ok=ok,
            approval_status="ready" if ok else login_status.lower(),
            message=f"Betfair login status: {login_status} (mode: {login_mode})",
        )

    def list_markets(self, category: str | None = None, max_results: int = 10) -> list[MarketSnapshot]:
        self._ensure_session_token()
        captured_at = datetime.now(timezone.utc)

        market_filter: dict[str, object] = {
            "marketStartTime": {
                "from": captured_at.replace(microsecond=0).isoformat().replace("+00:00", "Z")
            }
        }
        event_type_ids = self._event_type_ids_for_category(category)
        if event_type_ids:
            market_filter["eventTypeIds"] = event_type_ids
        market_type_codes = self._market_type_codes_for_category(category)
        if market_type_codes:
            market_filter["marketTypeCodes"] = market_type_codes

        catalogue = self._rpc_request(
            "SportsAPING/v1.0/listMarketCatalogue",
            {
                "filter": market_filter,
                "marketProjection": [
                    "COMPETITION",
                    "EVENT",
                    "EVENT_TYPE",
                    "MARKET_START_TIME",
                    "RUNNER_DESCRIPTION",
                ],
                "sort": "FIRST_TO_START",
                "maxResults": str(max_results),
            },
        )

        if not catalogue:
            return []

        market_ids = [market["marketId"] for market in catalogue if market.get("marketId")]
        books = self._rpc_request(
            "SportsAPING/v1.0/listMarketBook",
            {
                "marketIds": market_ids,
                "priceProjection": {"priceData": ["EX_BEST_OFFERS", "EX_TRADED"]},
            },
        )
        books_by_market_id = {book.get("marketId"): book for book in books}

        snapshots = []
        for market in catalogue:
            snapshot = self.normalize_market(market, books_by_market_id.get(market.get("marketId")))
            snapshot.captured_at = captured_at
            for selection in snapshot.selections:
                selection.captured_at = captured_at
            snapshots.append(snapshot)
        return snapshots

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
    def normalize_market(raw_market: dict, raw_book: dict | None = None) -> MarketSnapshot:
        """
        Normalize Betfair market catalogue and book data into a MarketSnapshot.

        Args:
            raw_market: Betfair listMarketCatalogue response for a single market
            raw_book: Optional Betfair listMarketBook response for the same market

        Returns:
            Normalized MarketSnapshot with all selections
        """
        raw_book = raw_book or {}
        runners_by_id = {str(runner.get("selectionId")): runner for runner in raw_book.get("runners", [])}

        def top_offer(offers: list[dict] | None) -> tuple[float | None, float | None]:
            if not offers:
                return None, None
            offer = offers[0] or {}
            return offer.get("price"), offer.get("size")

        def traded_volume(ex: dict, runner_book: dict) -> float | None:
            traded = ex.get("tradedVolume") or []
            if traded:
                return round(sum(float(item.get("size") or 0.0) for item in traded), 4)
            value = runner_book.get("totalMatched")
            return float(value) if value is not None else None

        # Parse event start time
        event_start = raw_market.get("marketStartTime")
        parsed_start = None
        if event_start:
            parsed_start = datetime.fromisoformat(event_start.replace("Z", "+00:00"))

        # Infer category from event type
        event_type = raw_market.get("eventType", {})
        event_type_id = event_type.get("id") if isinstance(event_type, dict) else None
        category, subcategory = infer_betfair_category(event_type_id)
        event = raw_market.get("event", {})
        competition = raw_market.get("competition", {})
        event_name = event.get("name") if isinstance(event, dict) else None
        competition_name = competition.get("name") if isinstance(competition, dict) else None

        # Normalize status
        raw_status = raw_market.get("description", {}).get("marketStatus") or raw_book.get("status")
        status = normalize_status(raw_status, "betfair")

        selections = []
        for runner in raw_market.get("runners", []):
            selection_id = str(runner.get("selectionId", ""))
            runner_book = runners_by_id.get(selection_id, {})
            ex = runner_book.get("ex", {})
            best_back, best_back_size = top_offer(ex.get("availableToBack"))
            best_lay, best_lay_size = top_offer(ex.get("availableToLay"))
            last_traded = runner_book.get("lastPriceTraded")
            selections.append(
                SelectionSnapshot(
                    exchange="betfair",
                    market_id=raw_market.get("marketId", ""),
                    selection_id=selection_id,
                    market_title=raw_market.get("marketName", ""),
                    selection_name=runner.get("runnerName", selection_id),
                    category=category,
                    subcategory=subcategory,
                    event_start=parsed_start,
                    best_back=best_back,
                    best_lay=best_lay,
                    last_traded=last_traded,
                    status=status,
                    event_name=event_name,
                    competition_name=competition_name,
                    best_back_size=best_back_size,
                    best_lay_size=best_lay_size,
                    traded_volume=traded_volume(ex, runner_book),
                    total_matched=runner_book.get("totalMatched"),
                    raw_payload={"catalogue": runner, "book": runner_book},
                )
            )

        return MarketSnapshot(
            exchange="betfair",
            market_id=raw_market.get("marketId", ""),
            market_title=raw_market.get("marketName", ""),
            category=category,
            subcategory=subcategory,
            event_start=parsed_start,
            status=status,
            selections=selections,
            event_name=event_name,
            competition_name=competition_name,
            total_matched=raw_book.get("totalMatched"),
            total_available=raw_book.get("totalAvailable"),
            in_play=raw_book.get("inplay"),
            is_market_data_delayed=raw_book.get("isMarketDataDelayed"),
            raw_payload={"catalogue": raw_market, "book": raw_book},
        )
