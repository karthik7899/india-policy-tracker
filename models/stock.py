"""Typed canonical model for a watchlist stock record.

The stock record has historically been an untyped dict whose numeric fields
are strings in display format ("482.95", "+23.0%"), parsed ad-hoc wherever
they're consumed — the class of bug this model retires. ``Stock`` holds
every numeric field as an actual number (coerced tolerantly from any format
the pipeline has ever produced), and ``to_wire_values()`` renders them back
into the exact legacy strings, so formatting happens in exactly one place.

``normalize_stock_record`` is the load-boundary hook: it canonicalizes a
raw dict's known fields while preserving key order and every unknown field
untouched — a well-formed record round-trips byte-identically (verified
against the full production watchlist.json), and a drifted one ("1,840.00",
a float where a string belongs, "N/A" in a numeric slot) is repaired on
entry instead of exploding mid-pipeline.
"""

from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, field_validator

from utils import to_float

# Fields rendered as 2-decimal money strings on the wire ("482.95").
_MONEY_FIELDS = ("price", "target", "target_median", "target_high", "target_low")
# Fields rendered as signed 1-decimal percent strings ("+23.0%", "-9.2%").
_PERCENT_FIELDS = ("growth_pct", "revenue_growth", "earnings_growth")
# Fields kept as bare numbers on the wire.
_NUMERIC_FIELDS = ("rec_score", "fundamental_value")


class Stock(BaseModel):
    """Canonical typed view of one watchlist stock. Unknown fields
    (screener, score, estimate_method, ...) pass through untouched."""

    model_config = ConfigDict(extra="allow")

    ticker: str
    name: str = ""
    catalyst: str = ""
    rating: str = "N/A"

    price: Optional[float] = None
    target: Optional[float] = None
    target_median: Optional[float] = None
    target_high: Optional[float] = None
    target_low: Optional[float] = None

    growth_pct: Optional[float] = None
    revenue_growth: Optional[float] = None
    earnings_growth: Optional[float] = None

    analyst_count: Optional[int] = None
    rec_score: Optional[float] = None
    fundamental_value: Optional[float] = None

    @field_validator(
        "price",
        "target",
        "target_median",
        "target_high",
        "target_low",
        "growth_pct",
        "revenue_growth",
        "earnings_growth",
        "rec_score",
        "fundamental_value",
        mode="before",
    )
    @classmethod
    def _coerce_float(cls, value):
        return to_float(value)

    @field_validator("analyst_count", mode="before")
    @classmethod
    def _coerce_int(cls, value):
        as_float = to_float(value)
        return None if as_float is None else int(as_float)

    @field_validator("rating", mode="before")
    @classmethod
    def _coerce_rating(cls, value):
        return "N/A" if value is None else str(value)

    def to_wire_values(self) -> Dict[str, Any]:
        """Every typed field rendered in the legacy on-disk/display format."""
        wire: Dict[str, Any] = {
            "ticker": self.ticker,
            "name": self.name,
            "catalyst": self.catalyst,
            "rating": self.rating,
            "analyst_count": self.analyst_count,
        }
        for field in _MONEY_FIELDS:
            value = getattr(self, field)
            wire[field] = None if value is None else f"{value:.2f}"
        for field in _PERCENT_FIELDS:
            value = getattr(self, field)
            if value is None:
                wire[field] = None
            else:
                sign = "+" if value > 0 else ""
                wire[field] = f"{sign}{value:.1f}%"
        for field in _NUMERIC_FIELDS:
            wire[field] = getattr(self, field)
        return wire


def normalize_stock_record(record: Dict[str, Any]) -> Dict[str, Any]:
    """Canonicalize a raw stock dict's known fields, preserving key order
    and all unknown fields. Raises pydantic.ValidationError for records
    broken beyond repair (e.g. no ticker) — callers decide whether to keep
    the raw dict instead."""
    wire = Stock.model_validate(record).to_wire_values()
    return {key: wire[key] if key in wire else value for key, value in record.items()}
