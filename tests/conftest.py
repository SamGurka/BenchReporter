from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SAMPLE_DATA = PROJECT_ROOT / "tests" / "data" / "sleeper_2025_sample"


def load_sample(relative_path: str) -> Any:
    return json.loads((SAMPLE_DATA / relative_path).read_text(encoding="utf-8"))


@pytest.fixture
def sample_league() -> dict[str, Any]:
    return load_sample("league.json")


@pytest.fixture
def week01_matchups() -> list[dict[str, Any]]:
    return load_sample("weeks/01/matchups.json")


@pytest.fixture
def week01_transactions() -> list[dict[str, Any]]:
    return load_sample("weeks/01/transactions.json")


@pytest.fixture
def week16_matchups() -> list[dict[str, Any]]:
    return load_sample("weeks/16/matchups.json")
