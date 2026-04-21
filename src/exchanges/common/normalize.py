"""Shared normalization utilities and category inference helpers."""

from __future__ import annotations

from typing import Optional

# Betfair event type IDs mapped to categories
BETFAIR_EVENT_TYPE_MAP: dict[str, tuple[str, str]] = {
    "1": ("sports", "soccer"),
    "2": ("sports", "tennis"),
    "3": ("sports", "golf"),
    "4": ("sports", "cricket"),
    "5": ("sports", "rugby_union"),
    "6": ("sports", "boxing"),
    "7": ("sports", "horse_racing"),
    "8": ("sports", "motor_sport"),
    "1477": ("sports", "rugby_league"),
    "4339": ("sports", "greyhound_racing"),
    "6231": ("finance", "financial_bets"),
    "6422": ("sports", "mma"),
    "6423": ("sports", "basketball"),
    "7511": ("sports", "baseball"),
    "7522": ("sports", "ice_hockey"),
    "7524": ("sports", "american_football"),
    "998917": ("sports", "volleyball"),
    "10": ("special", "special_bets"),
    "2378961": ("politics", "politics"),
}

# Smarkets slug-based category inference
SMARKETS_SLUG_PREFIXES: dict[str, tuple[str, str]] = {
    "football/": ("sports", "soccer"),
    "soccer/": ("sports", "soccer"),
    "tennis/": ("sports", "tennis"),
    "basketball/": ("sports", "basketball"),
    "american-football/": ("sports", "american_football"),
    "baseball/": ("sports", "baseball"),
    "ice-hockey/": ("sports", "ice_hockey"),
    "golf/": ("sports", "golf"),
    "cricket/": ("sports", "cricket"),
    "rugby/": ("sports", "rugby_union"),
    "mma/": ("sports", "mma"),
    "boxing/": ("sports", "boxing"),
    "horse-racing/": ("sports", "horse_racing"),
    "greyhound-racing/": ("sports", "greyhound_racing"),
    "motor-sport/": ("sports", "motor_sport"),
    "politics/": ("politics", "politics"),
    "entertainment/": ("entertainment", "entertainment"),
    "tv/": ("entertainment", "tv"),
    "current-affairs/": ("current_affairs", "current_affairs"),
}


def infer_betfair_category(event_type_id: Optional[str]) -> tuple[str, str]:
    """
    Infer category and subcategory from Betfair event type ID.

    Returns:
        Tuple of (category, subcategory). Defaults to ("unknown", "unknown").
    """
    if not event_type_id:
        return ("unknown", "unknown")
    return BETFAIR_EVENT_TYPE_MAP.get(str(event_type_id), ("unknown", "unknown"))


def infer_smarkets_category(full_slug: Optional[str]) -> tuple[str, str]:
    """
    Infer category and subcategory from Smarkets event slug.

    Args:
        full_slug: The full slug like "football/england/premier-league/arsenal-vs-chelsea"

    Returns:
        Tuple of (category, subcategory). Defaults to ("unknown", "unknown").
    """
    if not full_slug:
        return ("unknown", "unknown")

    slug_lower = full_slug.lower()
    for prefix, (category, subcategory) in SMARKETS_SLUG_PREFIXES.items():
        if slug_lower.startswith(prefix):
            return (category, subcategory)

    return ("unknown", "unknown")


def normalize_status(raw_status: Optional[str], exchange: str) -> str:
    """
    Normalize market status to a consistent format.

    Args:
        raw_status: The raw status string from the exchange
        exchange: The exchange name (betfair, smarkets)

    Returns:
        Normalized status string: open, suspended, closed, unknown
    """
    if not raw_status:
        return "unknown"

    status_lower = raw_status.lower()

    # Betfair statuses
    if exchange == "betfair":
        if status_lower in ("open", "active"):
            return "open"
        if status_lower == "suspended":
            return "suspended"
        if status_lower in ("closed", "inactive"):
            return "closed"

    # Smarkets statuses
    if exchange == "smarkets":
        if status_lower == "live":
            return "open"
        if status_lower == "halted":
            return "suspended"
        if status_lower in ("settled", "voided", "cancelled"):
            return "closed"

    return status_lower


def smarkets_price_to_decimal(price_int: Optional[int]) -> Optional[float]:
    """
    Convert Smarkets price (basis points) to decimal odds.

    Smarkets prices are in basis points (e.g., 2500 = 25.00% implied probability).
    Decimal odds = 10000 / price_int

    Args:
        price_int: Price in basis points (0-10000)

    Returns:
        Decimal odds, or None if invalid
    """
    if price_int is None or price_int <= 0 or price_int > 10000:
        return None
    return 10000 / price_int
