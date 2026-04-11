from __future__ import annotations

from statistics import mean, pstdev
from typing import Any

from .family_definitions import StrategyFamily
from .family_evaluator import CostModel, backtest_family


def run_robustness_tests(data_splits: dict[str, list[dict[str, Any]]], family: StrategyFamily, base_cost: CostModel) -> dict[str, Any]:
    stress_fee = CostModel(fee_bps=base_cost.fee_bps * 1.6, slippage_bps=base_cost.slippage_bps)
    stress_slip = CostModel(fee_bps=base_cost.fee_bps, slippage_bps=base_cost.slippage_bps * 2.0)

    baseline_oos, _ = backtest_family(data_splits["oos"], family, base_cost, "oos")
    elevated_fee_oos, _ = backtest_family(data_splits["oos"], family, stress_fee, "oos_fee")
    elevated_slip_oos, _ = backtest_family(data_splits["oos"], family, stress_slip, "oos_slip")

    perturb_pnls = []
    for bump in [0.9, 1.1]:
        p = dict(family.parameters)
        p["lookback"] = max(4, int(p["lookback"] * bump))
        p["stop_atr"] = max(0.3, p["stop_atr"] * bump)
        perturbed = StrategyFamily(family.family_id, family.family_name, family.hypothesis_class, family.rule_summary, p)
        _, m = backtest_family(data_splits["validation"], perturbed, base_cost, f"perturb_{bump}")
        perturb_pnls.append(m["net_pnl"])

    base_oos_pnl = sum(t["net_pnl"] for t in baseline_oos)
    fee_oos_pnl = sum(t["net_pnl"] for t in elevated_fee_oos)
    slip_oos_pnl = sum(t["net_pnl"] for t in elevated_slip_oos)

    outlier_ratio = 0.0
    if baseline_oos:
        sorted_abs = sorted((abs(t["net_pnl"]) for t in baseline_oos), reverse=True)
        k = max(1, int(len(sorted_abs) * 0.05))
        total = sum(sorted_abs)
        outlier_ratio = (sum(sorted_abs[:k]) / total) if total else 0.0

    return {
        "family_id": family.family_id,
        "fee_stress_pnl_delta": fee_oos_pnl - base_oos_pnl,
        "slippage_stress_pnl_delta": slip_oos_pnl - base_oos_pnl,
        "parameter_stability": mean(perturb_pnls) - pstdev(perturb_pnls),
        "outlier_dependence": outlier_ratio,
        "baseline_oos_trade_count": len(baseline_oos),
    }
