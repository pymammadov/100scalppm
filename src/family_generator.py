from __future__ import annotations

import itertools
import random

from .family_definitions import HYPOTHESIS_CLASSES, StrategyFamily

ENTRY_BLOCKS = [
    "range_breakout",
    "range_breakdown",
    "pullback_reentry",
    "failed_breakout_fade",
    "failed_breakdown_fade",
    "vwap_reclaim",
    "vwap_rejection",
    "overextension_revert",
    "liquidity_sweep_reclaim",
    "momentum_continuation",
    "session_open_burst",
    "compression_breakout",
]

EXIT_BLOCKS = ["fixed_stop_fixed_tp", "atr_stop_fixed_tp", "atr_stop_trailing", "time_stop_plus_tp", "vwap_reversion_exit", "momentum_failure_exit"]
REGIME_BLOCKS = ["uptrend_only", "downtrend_only", "high_vol_only", "low_vol_only", "sideways_disabled", "adaptive_by_vol"]
CONFIRMATION_BLOCKS = ["rsi_filter", "ema_alignment", "atr_filter", "vwap_distance", "range_percentile", "session_filter"]


def _base_params(hypothesis_class: str, entry: str, exit_block: str, regime: str, conf: str, idx: int) -> dict:
    rnd = random.Random(hash((hypothesis_class, entry, exit_block, regime, conf, idx)) & 0xFFFFFFFF)
    return {
        "entry_block": entry,
        "exit_block": exit_block,
        "regime_block": regime,
        "confirmation": conf,
        "position_mode": rnd.choice(["long_short", "long_only", "short_only"]),
        "lookback": rnd.choice([8, 12, 16, 20, 30]),
        "stop_atr": rnd.choice([0.7, 0.9, 1.1, 1.4, 1.8]),
        "tp_r": rnd.choice([0.8, 1.0, 1.2, 1.5, 2.0]),
        "trail_atr": rnd.choice([0.7, 1.0, 1.3, 1.6]),
        "time_stop_bars": rnd.choice([15, 25, 40, 60]),
        "rsi_len": rnd.choice([7, 9, 14]),
        "rsi_band": rnd.choice([25, 30, 35, 65, 70, 75]),
        "ema_fast": rnd.choice([8, 12, 21]),
        "ema_slow": rnd.choice([34, 55, 89]),
        "throttle_bars": rnd.choice([2, 3, 5, 8, 13]),
        "risk_per_trade": rnd.choice([0.001, 0.002, 0.003]),
        "volatility_window": rnd.choice([20, 30, 50]),
    }


def generate_strategy_families(n_families: int = 120) -> list[StrategyFamily]:
    per_class = max(1, n_families // len(HYPOTHESIS_CLASSES))
    remainder = n_families % len(HYPOTHESIS_CLASSES)
    families: list[StrategyFamily] = []
    idx = 0
    for c_idx, hypothesis_class in enumerate(HYPOTHESIS_CLASSES):
        target = per_class + (1 if c_idx < remainder else 0)
        combos = itertools.product(ENTRY_BLOCKS, EXIT_BLOCKS, REGIME_BLOCKS, CONFIRMATION_BLOCKS)
        for entry, exit_block, regime, conf in combos:
            if target <= 0:
                break
            params = _base_params(hypothesis_class, entry, exit_block, regime, conf, idx)
            family_id = f"FAM_{idx:04d}"
            family_name = f"{hypothesis_class}_{entry}_{exit_block}_{idx:04d}"
            summary = f"{hypothesis_class} using {entry}, confirmed by {conf}, gated by {regime}, exited via {exit_block}."
            families.append(
                StrategyFamily(
                    family_id=family_id,
                    family_name=family_name,
                    hypothesis_class=hypothesis_class,
                    rule_summary=summary,
                    parameters=params,
                )
            )
            idx += 1
            target -= 1
            if len(families) >= n_families:
                return families
    return families
