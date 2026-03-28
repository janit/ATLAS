"""Pattern cache domain models.

Covers the Ebbinghaus-decay pattern cache: Pattern (stored in Redis),
PatternType / PatternTier enums, PatternScore (transient scoring wrapper),
and the HALF_LIVES lookup table.
"""

from __future__ import annotations

import enum
from datetime import datetime, timezone
from typing import List, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class PatternType(str, enum.Enum):
    """Category of a cached code pattern."""

    ERROR_FIX = "error_fix"
    API_PATTERN = "api_pattern"
    BUG_FIX = "bug_fix"
    ARCHITECTURAL = "architectural"
    IDIOM = "idiom"


class PatternTier(str, enum.Enum):
    """Memory tier for a cached pattern."""

    STM = "stm"           # Short-term memory (capacity-limited)
    LTM = "ltm"           # Long-term memory (promoted from STM)
    PERSISTENT = "persistent"  # Seed patterns, never decay


# ---------------------------------------------------------------------------
# Half-life lookup (days) per pattern type
# ---------------------------------------------------------------------------

HALF_LIVES: dict[PatternType, float] = {
    PatternType.ERROR_FIX: 7.0,
    PatternType.API_PATTERN: 14.0,
    PatternType.BUG_FIX: 10.0,
    PatternType.ARCHITECTURAL: 21.0,
    PatternType.IDIOM: 14.0,
}


# ---------------------------------------------------------------------------
# Core model
# ---------------------------------------------------------------------------

class Pattern(BaseModel):
    """A cached reusable code pattern with Ebbinghaus decay metadata."""

    id: str
    type: PatternType
    tier: PatternTier = PatternTier.STM
    content: str = ""
    summary: str = ""
    context_query: str = ""
    error_context: Optional[str] = None
    surprise_score: float = 0.0
    access_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    half_life_days: float = 14.0
    source_files: List[str] = Field(default_factory=list)
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    last_accessed: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    # ------------------------------------------------------------------
    # Computed helpers (used by scorer / consolidator)
    # ------------------------------------------------------------------

    def days_since_access(self) -> float:
        """Days elapsed since *last_accessed*."""
        try:
            last = datetime.fromisoformat(self.last_accessed)
            if last.tzinfo is None:
                last = last.replace(tzinfo=timezone.utc)
            delta = datetime.now(timezone.utc) - last
            return max(delta.total_seconds() / 86400.0, 0.0)
        except (ValueError, TypeError):
            return 0.0

    def age_days(self) -> float:
        """Days elapsed since *created_at*."""
        try:
            created = datetime.fromisoformat(self.created_at)
            if created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)
            delta = datetime.now(timezone.utc) - created
            return max(delta.total_seconds() / 86400.0, 0.0)
        except (ValueError, TypeError):
            return 0.0

    def success_rate(self) -> float:
        """Fraction of accesses that were successes."""
        total = self.success_count + self.failure_count
        if total == 0:
            return 0.0
        return self.success_count / total


# ---------------------------------------------------------------------------
# Transient scoring wrapper (never persisted)
# ---------------------------------------------------------------------------

class PatternScore(BaseModel):
    """Result of scoring a Pattern against a query."""

    pattern: Pattern
    similarity: float = 0.0
    decay_factor: float = 1.0
    frequency_boost: float = 1.0
    composite_score: float = 0.0
