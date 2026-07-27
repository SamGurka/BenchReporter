"""Scoring profile detection for Sleeper league settings."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


STANDARD_SCORING = {
    "pass_yd": 0.04,
    "pass_td": 4.0,
    "pass_int": -2.0,
    "rush_yd": 0.1,
    "rush_td": 6.0,
    "rec_yd": 0.1,
    "rec_td": 6.0,
    "fum_lost": -2.0,
}


@dataclass(frozen=True)
class ScoringProfile:
    name: str
    stats_field: str | None
    supported_for_generic_stats: bool
    reason: str | None = None


def _number(value: Any) -> float:
    if value is None:
        return 0.0
    return float(value)


def detect_scoring_profile(scoring_settings: dict[str, Any]) -> ScoringProfile:
    """Map Sleeper scoring settings to a generic stats field when safe.

    Sleeper's stats endpoint exposes `pts_std`, `pts_half_ppr`, and `pts_ppr`.
    Those fields are only safe when the league scoring matches a standard
    profile closely enough. If meaningful custom scoring is present, callers
    should avoid using generic free-agent point fields.
    """

    custom_keys = []
    for key, standard_value in STANDARD_SCORING.items():
        if _number(scoring_settings.get(key)) != standard_value:
            custom_keys.append(key)

    rec = _number(scoring_settings.get("rec"))
    if rec not in {0.0, 0.5, 1.0}:
        custom_keys.append("rec")

    ignored_keys = set(STANDARD_SCORING) | {"rec"}
    extra_nonzero = [
        key
        for key, value in scoring_settings.items()
        if key not in ignored_keys and _number(value) != 0.0
    ]

    if custom_keys or extra_nonzero:
        details = []
        if custom_keys:
            details.append(f"non-standard core keys: {', '.join(sorted(custom_keys))}")
        if extra_nonzero:
            details.append(f"extra scoring keys: {', '.join(sorted(extra_nonzero)[:8])}")
        return ScoringProfile(
            name="custom",
            stats_field=None,
            supported_for_generic_stats=False,
            reason="; ".join(details),
        )

    if rec == 1.0:
        return ScoringProfile("ppr", "pts_ppr", True)
    if rec == 0.5:
        return ScoringProfile("half_ppr", "pts_half_ppr", True)
    return ScoringProfile("standard", "pts_std", True)

