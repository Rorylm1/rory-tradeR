from __future__ import annotations

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATA_ROOT = REPO_ROOT / "data"
EXTRACTED_LITE_DATA_ROOT = REPO_ROOT / "runtime" / "quarantine" / "extracted-lite" / "data"
DATA_ROOT_ENV_VAR = "RORY_TRADER_DATA_ROOT"


def _resolve_repo_relative(path_str: str) -> Path:
    candidate = Path(path_str).expanduser()
    if candidate.is_absolute():
        return candidate.resolve()
    return (REPO_ROOT / candidate).resolve()


def _has_dataset_layout(root: Path) -> bool:
    return (root / "kalshi").exists() or (root / "polymarket").exists()


def get_data_root() -> Path:
    configured = os.getenv(DATA_ROOT_ENV_VAR)
    if configured:
        return _resolve_repo_relative(configured)

    if _has_dataset_layout(EXTRACTED_LITE_DATA_ROOT) and not _has_dataset_layout(DEFAULT_DATA_ROOT):
        return EXTRACTED_LITE_DATA_ROOT

    return DEFAULT_DATA_ROOT


def data_path(*parts: str) -> Path:
    return get_data_root().joinpath(*parts)
