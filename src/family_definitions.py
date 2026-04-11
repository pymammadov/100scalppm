from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any


HYPOTHESIS_CLASSES = [
    "breakout_scalp",
    "breakdown_scalp",
    "pullback_continuation",
    "failed_breakout_fade",
    "failed_breakdown_fade",
    "vwap_reversion",
    "overextension_snapback",
    "compression_expansion_breakout",
    "session_open_impulse",
    "trend_reentry_scalp",
    "liquidity_sweep_reclaim",
    "volatility_regime_adaptive",
    "hybrid_continuation_fade",
    "short_only_bear_regime",
    "long_only_expansion",
]


@dataclass(frozen=True)
class StrategyFamily:
    family_id: str
    family_name: str
    hypothesis_class: str
    rule_summary: str
    parameters: dict[str, Any]

    def as_catalog_row(self) -> dict[str, Any]:
        row = asdict(self)
        row["parameter_json"] = str(self.parameters)
        row.pop("parameters")
        return row
