from __future__ import annotations

from src.exchanges import BetfairAdapter, SmarketsAdapter


def run_doctor() -> list[str]:
    lines: list[str] = []
    adapters = [BetfairAdapter(), SmarketsAdapter()]
    for adapter in adapters:
        result = adapter.validate_credentials()
        prefix = "OK" if result.ok else "WARN"
        lines.append(f"[{prefix}] {result.exchange}: {result.message}")
        if result.details:
            for key, value in result.details.items():
                lines.append(f"    {key}: {value}")
    return lines
