"""Tests for Betfair market normalization."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from src.exchanges.betfair.adapter import BetfairAdapter
from src.exchanges.common.models import MarketSnapshot, SelectionSnapshot

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "betfair"


@pytest.fixture
def betfair_catalogue() -> dict:
    """Load sample Betfair market catalogue fixture."""
    with open(FIXTURES_DIR / "market_catalogue.json") as f:
        return json.load(f)


@pytest.fixture
def betfair_book() -> dict:
    """Load sample Betfair market book fixture."""
    with open(FIXTURES_DIR / "market_book.json") as f:
        return json.load(f)


class TestBetfairNormalization:
    """Test suite for Betfair market normalization."""

    def test_normalize_market_returns_market_snapshot(self, betfair_catalogue: dict, betfair_book: dict):
        """normalize_market should return a MarketSnapshot."""
        result = BetfairAdapter.normalize_market(betfair_catalogue, betfair_book)
        assert isinstance(result, MarketSnapshot)

    def test_normalized_market_has_required_fields(self, betfair_catalogue: dict, betfair_book: dict):
        """Normalized market should have all required fields."""
        result = BetfairAdapter.normalize_market(betfair_catalogue, betfair_book)

        assert result.exchange == "betfair"
        assert result.market_id == "1.234567890"
        assert result.market_title == "Match Odds"
        assert result.category == "sports"
        assert result.subcategory == "soccer"
        assert result.event_start is not None
        assert result.status == "open"
        assert result.total_matched == 125000.50
        assert result.total_available == 45000.00
        assert result.in_play is False
        assert result.is_market_data_delayed is False
        assert isinstance(result.raw_payload, dict)

    def test_normalized_selections_have_required_fields(self, betfair_catalogue: dict, betfair_book: dict):
        """Each selection should have all required fields."""
        result = BetfairAdapter.normalize_market(betfair_catalogue, betfair_book)

        assert len(result.selections) == 3

        for selection in result.selections:
            assert isinstance(selection, SelectionSnapshot)
            assert selection.exchange == "betfair"
            assert selection.market_id == "1.234567890"
            assert selection.selection_id != ""
            assert selection.market_title == "Match Odds"
            assert selection.selection_name != ""
            assert selection.category == "sports"
            assert selection.subcategory == "soccer"
            assert selection.event_start is not None
            assert selection.best_back is not None
            assert selection.best_lay is not None
            assert selection.last_traded is not None
            assert selection.status == "open"
            assert isinstance(selection.raw_payload, dict)

    def test_selection_prices_are_correct(self, betfair_catalogue: dict, betfair_book: dict):
        """Selection prices should match fixture data."""
        result = BetfairAdapter.normalize_market(betfair_catalogue, betfair_book)

        # Find Arsenal selection (selectionId 1001)
        arsenal = next(s for s in result.selections if s.selection_id == "1001")
        assert arsenal.selection_name == "Arsenal"
        assert arsenal.best_back == 2.48
        assert arsenal.best_back_size == 500.00
        assert arsenal.best_lay == 2.52
        assert arsenal.best_lay_size == 450.00
        assert arsenal.last_traded == 2.50
        assert arsenal.total_matched == 50000.00

    def test_event_start_is_parsed_correctly(self, betfair_catalogue: dict, betfair_book: dict):
        """Event start time should be parsed as UTC datetime."""
        result = BetfairAdapter.normalize_market(betfair_catalogue, betfair_book)

        expected = datetime(2025, 6, 15, 14, 0, 0, tzinfo=timezone.utc)
        assert result.event_start == expected

    def test_normalize_without_book_data(self, betfair_catalogue: dict):
        """Normalization should work without book data (prices will be None)."""
        result = BetfairAdapter.normalize_market(betfair_catalogue, None)

        assert result.exchange == "betfair"
        assert len(result.selections) == 3
        for selection in result.selections:
            assert selection.best_back is None
            assert selection.best_lay is None
            assert selection.last_traded is None
            assert selection.best_back_size is None
            assert selection.best_lay_size is None

    def test_category_inference_for_soccer(self, betfair_catalogue: dict, betfair_book: dict):
        """Soccer event type should map to sports/soccer category."""
        result = BetfairAdapter.normalize_market(betfair_catalogue, betfair_book)
        assert result.category == "sports"
        assert result.subcategory == "soccer"

    def test_category_inference_unknown_event_type(self, betfair_book: dict):
        """Unknown event type should map to unknown/unknown."""
        catalogue = {
            "marketId": "1.999",
            "marketName": "Test",
            "eventType": {"id": "99999", "name": "Unknown"},
            "runners": [],
        }
        result = BetfairAdapter.normalize_market(catalogue, betfair_book)
        assert result.category == "unknown"
        assert result.subcategory == "unknown"

    def test_raw_payload_preserved(self, betfair_catalogue: dict, betfair_book: dict):
        """Raw payload should preserve original API response."""
        result = BetfairAdapter.normalize_market(betfair_catalogue, betfair_book)

        assert "catalogue" in result.raw_payload
        assert "book" in result.raw_payload
        assert result.raw_payload["catalogue"] == betfair_catalogue

    def test_implied_probability_calculation(self, betfair_catalogue: dict, betfair_book: dict):
        """SelectionSnapshot.implied_probability should calculate correctly."""
        result = BetfairAdapter.normalize_market(betfair_catalogue, betfair_book)

        arsenal = next(s for s in result.selections if s.selection_id == "1001")
        # last_traded = 2.50, so implied probability = 1/2.50 = 0.4
        assert arsenal.implied_probability == pytest.approx(0.4, rel=0.01)


class TestBetfairMarketDiscovery:
    """Test suite for Betfair market discovery using mocked API responses."""

    def test_list_markets_returns_normalized_snapshots(self, betfair_catalogue: dict, betfair_book: dict, monkeypatch):
        adapter = BetfairAdapter()
        monkeypatch.setattr(adapter, "_ensure_session_token", lambda: None)

        def fake_rpc_request(method: str, params: dict):
            if method.endswith("listMarketCatalogue"):
                assert params["maxResults"] == "3"
                return [betfair_catalogue]
            if method.endswith("listMarketBook"):
                assert params["marketIds"] == ["1.234567890"]
                return [betfair_book]
            raise AssertionError(f"Unexpected method: {method}")

        monkeypatch.setattr(adapter, "_rpc_request", fake_rpc_request)

        snapshots = adapter.list_markets(category="sports", max_results=3)

        assert len(snapshots) == 1
        assert snapshots[0].market_id == "1.234567890"
        assert snapshots[0].selections[0].exchange == "betfair"

    def test_list_markets_batches_market_book_requests(self, betfair_catalogue: dict, betfair_book: dict, monkeypatch):
        adapter = BetfairAdapter()
        adapter.market_book_batch_size = 2
        monkeypatch.setattr(adapter, "_ensure_session_token", lambda: None)
        catalogue = [{**betfair_catalogue, "marketId": f"1.{index}"} for index in range(5)]
        book_calls = []

        def fake_rpc_request(method: str, params: dict):
            if method.endswith("listMarketCatalogue"):
                return catalogue
            if method.endswith("listMarketBook"):
                book_calls.append(params["marketIds"])
                return [{**betfair_book, "marketId": market_id} for market_id in params["marketIds"]]
            raise AssertionError(f"Unexpected method: {method}")

        monkeypatch.setattr(adapter, "_rpc_request", fake_rpc_request)

        snapshots = adapter.list_markets(category="tennis", max_results=5)

        assert len(snapshots) == 5
        assert book_calls == [["1.0", "1.1"], ["1.2", "1.3"], ["1.4"]]

    def test_list_market_books_batches_ids_for_settlement(self, betfair_book: dict, monkeypatch):
        adapter = BetfairAdapter()
        adapter.market_book_batch_size = 2
        monkeypatch.setattr(adapter, "_ensure_session_token", lambda: None)
        book_calls = []

        def fake_rpc_request(method: str, params: dict):
            assert method.endswith("listMarketBook")
            book_calls.append(params["marketIds"])
            assert params["priceProjection"]["priceData"] == ["EX_TRADED"]
            return [{**betfair_book, "marketId": market_id} for market_id in params["marketIds"]]

        monkeypatch.setattr(adapter, "_rpc_request", fake_rpc_request)

        books = adapter.list_market_books(["1.0", "1.1", "1.0", "1.2"])

        assert [book["marketId"] for book in books] == ["1.0", "1.1", "1.2"]
        assert book_calls == [["1.0", "1.1"], ["1.2"]]

    def test_tennis_list_markets_uses_high_signal_market_types(
        self, betfair_catalogue: dict, betfair_book: dict, monkeypatch
    ):
        adapter = BetfairAdapter()
        monkeypatch.setattr(adapter, "_ensure_session_token", lambda: None)

        def fake_rpc_request(method: str, params: dict):
            if method.endswith("listMarketCatalogue"):
                market_filter = params["filter"]
                assert market_filter["eventTypeIds"] == ["2"]
                assert market_filter["marketTypeCodes"] == ["MATCH_ODDS", "SET_WINNER"]
                start_filter = market_filter["marketStartTime"]
                from_time = datetime.fromisoformat(start_filter["from"].replace("Z", "+00:00"))
                to_time = datetime.fromisoformat(start_filter["to"].replace("Z", "+00:00"))
                assert 29 <= (from_time - datetime.now(timezone.utc)).total_seconds() / 60 <= 31
                assert 71.9 <= (to_time - datetime.now(timezone.utc)).total_seconds() / 3600 <= 72.1
                return [betfair_catalogue]
            if method.endswith("listMarketBook"):
                assert params["priceProjection"]["priceData"] == ["EX_BEST_OFFERS", "EX_TRADED"]
                return [betfair_book]
            raise AssertionError(f"Unexpected method: {method}")

        monkeypatch.setattr(adapter, "_rpc_request", fake_rpc_request)

        snapshots = adapter.list_markets(category="tennis", max_results=3)

        assert len(snapshots) == 1

    def test_tennis_market_start_window_is_configurable(self, betfair_catalogue: dict, betfair_book: dict, monkeypatch):
        adapter = BetfairAdapter()
        monkeypatch.setenv("RORY_TRADER_BETFAIR_TENNIS_MIN_START_MINUTES", "90")
        monkeypatch.setenv("RORY_TRADER_BETFAIR_TENNIS_MAX_START_HOURS", "24")
        monkeypatch.setattr(adapter, "_ensure_session_token", lambda: None)

        def fake_rpc_request(method: str, params: dict):
            if method.endswith("listMarketCatalogue"):
                start_filter = params["filter"]["marketStartTime"]
                from_time = datetime.fromisoformat(start_filter["from"].replace("Z", "+00:00"))
                to_time = datetime.fromisoformat(start_filter["to"].replace("Z", "+00:00"))
                assert 89 <= (from_time - datetime.now(timezone.utc)).total_seconds() / 60 <= 91
                assert 23.9 <= (to_time - datetime.now(timezone.utc)).total_seconds() / 3600 <= 24.1
                return [betfair_catalogue]
            if method.endswith("listMarketBook"):
                return [betfair_book]
            raise AssertionError(f"Unexpected method: {method}")

        monkeypatch.setattr(adapter, "_rpc_request", fake_rpc_request)

        snapshots = adapter.list_markets(category="tennis", max_results=3)

        assert len(snapshots) == 1
