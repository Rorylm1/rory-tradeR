"""Tests for Smarkets market normalization."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from src.exchanges.smarkets.adapter import SmarketsAdapter
from src.exchanges.common.models import MarketSnapshot, SelectionSnapshot
from src.exchanges.common.normalize import smarkets_price_to_decimal

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "smarkets"


@pytest.fixture
def smarkets_markets() -> dict:
    """Load sample Smarkets markets fixture."""
    with open(FIXTURES_DIR / "markets.json") as f:
        return json.load(f)


@pytest.fixture
def smarkets_quotes() -> dict:
    """Load sample Smarkets quotes fixture."""
    with open(FIXTURES_DIR / "quotes.json") as f:
        return json.load(f)


@pytest.fixture
def single_market(smarkets_markets: dict) -> dict:
    """Extract single market from markets response."""
    return smarkets_markets["markets"][0]


@pytest.fixture
def quotes_by_contract(smarkets_quotes: dict) -> dict:
    """Extract quotes keyed by contract ID."""
    return smarkets_quotes["quotes"]


class TestSmarketsNormalization:
    """Test suite for Smarkets market normalization."""

    def test_normalize_market_returns_market_snapshot(
        self, single_market: dict, quotes_by_contract: dict
    ):
        """normalize_market should return a MarketSnapshot."""
        result = SmarketsAdapter.normalize_market(single_market, quotes_by_contract)
        assert isinstance(result, MarketSnapshot)

    def test_normalized_market_has_required_fields(
        self, single_market: dict, quotes_by_contract: dict
    ):
        """Normalized market should have all required fields."""
        result = SmarketsAdapter.normalize_market(single_market, quotes_by_contract)

        assert result.exchange == "smarkets"
        assert result.market_id == "sm-market-12345"
        assert result.market_title == "Match Winner"
        assert result.category == "sports"
        assert result.subcategory == "soccer"
        assert result.event_start is not None
        assert result.status == "open"
        assert isinstance(result.raw_payload, dict)

    def test_normalized_selections_have_required_fields(
        self, single_market: dict, quotes_by_contract: dict
    ):
        """Each selection should have all required fields."""
        result = SmarketsAdapter.normalize_market(single_market, quotes_by_contract)

        assert len(result.selections) == 3

        for selection in result.selections:
            assert isinstance(selection, SelectionSnapshot)
            assert selection.exchange == "smarkets"
            assert selection.market_id == "sm-market-12345"
            assert selection.selection_id != ""
            assert selection.market_title == "Match Winner"
            assert selection.selection_name != ""
            assert selection.category == "sports"
            assert selection.subcategory == "soccer"
            assert selection.event_start is not None
            assert selection.best_back is not None
            assert selection.best_lay is not None
            assert selection.last_traded is not None
            assert selection.status == "open"
            assert isinstance(selection.raw_payload, dict)

    def test_selection_prices_are_correct(
        self, single_market: dict, quotes_by_contract: dict
    ):
        """Selection prices should match fixture data (converted from basis points)."""
        result = SmarketsAdapter.normalize_market(single_market, quotes_by_contract)

        # Find Arsenal selection (contract sm-contract-001)
        arsenal = next(s for s in result.selections if s.selection_id == "sm-contract-001")
        assert arsenal.selection_name == "Arsenal"
        # 2480 basis points = 10000/2480 = 4.032 decimal odds
        assert arsenal.best_back == pytest.approx(4.032, rel=0.01)
        # 2520 basis points = 10000/2520 = 3.968 decimal odds
        assert arsenal.best_lay == pytest.approx(3.968, rel=0.01)
        # 2500 basis points = 10000/2500 = 4.0 decimal odds
        assert arsenal.last_traded == pytest.approx(4.0, rel=0.01)

    def test_event_start_is_parsed_correctly(
        self, single_market: dict, quotes_by_contract: dict
    ):
        """Event start time should be parsed as UTC datetime."""
        result = SmarketsAdapter.normalize_market(single_market, quotes_by_contract)

        expected = datetime(2025, 6, 15, 14, 0, 0, tzinfo=timezone.utc)
        assert result.event_start == expected

    def test_normalize_without_quotes_data(self, single_market: dict):
        """Normalization should work without quotes data (prices will be None)."""
        result = SmarketsAdapter.normalize_market(single_market, None)

        assert result.exchange == "smarkets"
        assert len(result.selections) == 3
        for selection in result.selections:
            assert selection.best_back is None
            assert selection.best_lay is None
            assert selection.last_traded is None

    def test_category_inference_from_slug(
        self, single_market: dict, quotes_by_contract: dict
    ):
        """Category should be inferred from event slug."""
        result = SmarketsAdapter.normalize_market(single_market, quotes_by_contract)
        assert result.category == "sports"
        assert result.subcategory == "soccer"

    def test_category_inference_unknown_slug(self, quotes_by_contract: dict):
        """Unknown slug should map to unknown/unknown."""
        market = {
            "id": "sm-market-999",
            "name": "Test",
            "state": "live",
            "event": {"full_slug": "weird/unknown/thing"},
            "contracts": [],
        }
        result = SmarketsAdapter.normalize_market(market, quotes_by_contract)
        assert result.category == "unknown"
        assert result.subcategory == "unknown"

    def test_raw_payload_preserved(
        self, single_market: dict, quotes_by_contract: dict
    ):
        """Raw payload should preserve original API response."""
        result = SmarketsAdapter.normalize_market(single_market, quotes_by_contract)

        assert "market" in result.raw_payload
        assert "quotes" in result.raw_payload
        assert result.raw_payload["market"] == single_market

    def test_implied_probability_calculation(
        self, single_market: dict, quotes_by_contract: dict
    ):
        """SelectionSnapshot.implied_probability should calculate correctly."""
        result = SmarketsAdapter.normalize_market(single_market, quotes_by_contract)

        arsenal = next(s for s in result.selections if s.selection_id == "sm-contract-001")
        # last_traded = 4.0 decimal odds, so implied probability = 1/4.0 = 0.25
        assert arsenal.implied_probability == pytest.approx(0.25, rel=0.01)


class TestSmarketsPriceConversion:
    """Test suite for Smarkets price conversion utilities."""

    def test_basis_points_to_decimal_odds(self):
        """Basis points should convert correctly to decimal odds."""
        assert smarkets_price_to_decimal(5000) == pytest.approx(2.0)
        assert smarkets_price_to_decimal(2500) == pytest.approx(4.0)
        assert smarkets_price_to_decimal(10000) == pytest.approx(1.0)
        assert smarkets_price_to_decimal(100) == pytest.approx(100.0)

    def test_invalid_prices_return_none(self):
        """Invalid prices should return None."""
        assert smarkets_price_to_decimal(None) is None
        assert smarkets_price_to_decimal(0) is None
        assert smarkets_price_to_decimal(-100) is None
        assert smarkets_price_to_decimal(10001) is None


class TestSmarketsValidation:
    """Test suite for Smarkets credential validation."""

    def test_validation_approval_required(self, monkeypatch):
        """Validation should report approval_required when API disabled."""
        monkeypatch.setenv("SMARKETS_API_ENABLED", "false")
        monkeypatch.setenv("SMARKETS_API_TOKEN", "test-token")

        adapter = SmarketsAdapter()
        result = adapter.validate_credentials()

        assert result.ok is False
        assert result.approval_status == "approval_required"

    def test_validation_missing_token(self, monkeypatch):
        """Validation should report missing_token when token not set."""
        monkeypatch.setenv("SMARKETS_API_ENABLED", "true")
        monkeypatch.setenv("SMARKETS_API_TOKEN", "")

        adapter = SmarketsAdapter()
        result = adapter.validate_credentials()

        assert result.ok is False
        assert result.approval_status == "missing_token"

    def test_validation_ready(self, monkeypatch):
        """Validation should report ready when properly configured."""
        monkeypatch.setenv("SMARKETS_API_ENABLED", "true")
        monkeypatch.setenv("SMARKETS_API_TOKEN", "valid-token")

        adapter = SmarketsAdapter()
        result = adapter.validate_credentials()

        assert result.ok is True
        assert result.approval_status == "ready"
