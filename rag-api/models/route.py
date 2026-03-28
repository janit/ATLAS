"""Confidence-router domain models.

Covers the Thompson Sampling route selector: Route / DifficultyBin enums,
SignalBundle, RouteDecision, the difficulty_to_bin helper, and the
FALLBACK_CHAIN / ROUTE_RETRY_BUDGET / ROUTE_COSTS lookup tables.
"""

from __future__ import annotations

import enum
from typing import Dict, Optional

from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class Route(str, enum.Enum):
    """Available inference routes, ordered by cost."""

    CACHE_HIT = "cache_hit"
    FAST_PATH = "fast_path"
    STANDARD = "standard"
    HARD_PATH = "hard_path"


class DifficultyBin(str, enum.Enum):
    """Discretised difficulty buckets for Thompson state."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


# ---------------------------------------------------------------------------
# Lookup tables
# ---------------------------------------------------------------------------

FALLBACK_CHAIN: Dict[Route, Optional[Route]] = {
    Route.CACHE_HIT: Route.FAST_PATH,
    Route.FAST_PATH: Route.STANDARD,
    Route.STANDARD: Route.HARD_PATH,
    Route.HARD_PATH: None,
}

ROUTE_RETRY_BUDGET: Dict[Route, int] = {
    Route.CACHE_HIT: 0,
    Route.FAST_PATH: 1,
    Route.STANDARD: 2,
    Route.HARD_PATH: 4,
}

ROUTE_COSTS: Dict[Route, float] = {
    Route.CACHE_HIT: 0.1,
    Route.FAST_PATH: 0.5,
    Route.STANDARD: 1.0,
    Route.HARD_PATH: 2.0,
}


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def difficulty_to_bin(difficulty: float) -> DifficultyBin:
    """Map a continuous difficulty score in [0, 1] to a discrete bin."""
    if difficulty < 0.3:
        return DifficultyBin.LOW
    if difficulty < 0.6:
        return DifficultyBin.MEDIUM
    return DifficultyBin.HIGH


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

class SignalBundle(BaseModel):
    """Collected routing signals fed into the difficulty estimator."""

    pattern_cache_score: float = 0.0
    retrieval_confidence: float = 0.0
    query_complexity: float = 0.0
    geometric_energy: float = 0.0


class RouteDecision(BaseModel):
    """Output of the Thompson Sampling route selector."""

    route: Route
    difficulty_score: float = 0.0
    difficulty_bin: DifficultyBin = DifficultyBin.MEDIUM
    retry_budget: int = 2
    signals: SignalBundle = SignalBundle()
    thompson_samples: Optional[Dict[str, float]] = None
    cache_hit_available: bool = False
