from __future__ import annotations

import argparse
import ast
import json
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from scripts.run_strategy_factory import maybe_make_sample
from src.family_evaluator import CostModel, backtest_family, prepare_features, split_dataset
from src.family_generator import generate_strategy_families
from src.ranking import rank_candidates
from src.robustness import run_robustness_tests
from src.strategy_factory import _read_csv_rows

TARGET_FAMILIES = {"FAM_0053", "FAM_0039"}


def _parse_bucket(value: str) -> dict[str, float]:
    try:
        parsed = ast.literal_eval(value)
        if isinstance(parsed, dict):
            return {str(k): float(v) for k, v in parsed.items()}
    except (ValueError, SyntaxError):
        pass
    return {}


def _equity_curve(trades: list[dict]) -> list[float]:
    c = 0.0
    out = []
    for t in trades:
        c += t["net_pnl"]
        out.append(c)
    return out


def _perturbation_report(splits: dict[str, list[dict]], fam, base_cost: CostModel) -> list[dict]:
    bumps = [0.85, 0.9, 1.1, 1.15]
    rows = []
    for bump in bumps:
        p = dict(fam.parameters)
        p["lookback"] = max(4, int(p["lookback"] * bump))
        p["stop_atr"] = max(0.3, p["stop_atr"] * bump)
        p["tp_r"] = max(0.5, p["tp_r"] * bump)
        fam_pert = type(fam)(
            family_id=f"{fam.family_id}_p{str(bump).replace('.', '')}",
            family_name=fam.family_name,
            hypothesis_class=fam.hypothesis_class,
            rule_summary=fam.rule_summary,
            parameters=p,
        )
        _, val_metrics = backtest_family(splits["validation"], fam_pert, base_cost, f"val_p_{bump}")
        _, oos_metrics = backtest_family(splits["oos"], fam_pert, base_cost, f"oos_p_{bump}")
        rows.append(
            {
                "bump": bump,
                "lookback": p["lookback"],
                "stop_atr": p["stop_atr"],
                "tp_r": p["tp_r"],
                "validation_net_pnl": val_metrics["net_pnl"],
                "oos_net_pnl": oos_metrics["net_pnl"],
                "oos_trade_count": oos_metrics["trade_count"],
            }
        )
    return rows


def _deep_dive_for_family(fam, splits: dict[str, list[dict]], base_cost: CostModel) -> dict:
    oos_trades, oos_metrics = backtest_family(splits["oos"], fam, base_cost, "oos")
    fee_stress_cost = CostModel(fee_bps=base_cost.fee_bps * 1.6, slippage_bps=base_cost.slippage_bps)
    slip_stress_cost = CostModel(fee_bps=base_cost.fee_bps, slippage_bps=base_cost.slippage_bps * 2.0)

    _, fee_metrics = backtest_family(splits["oos"], fam, fee_stress_cost, "oos_fee")
    _, slip_metrics = backtest_family(splits["oos"], fam, slip_stress_cost, "oos_slippage")

    robust = run_robustness_tests(splits, fam, base_cost)

    return {
        "family_id": fam.family_id,
        "family_name": fam.family_name,
        "hypothesis_class": fam.hypothesis_class,
        "parameters": fam.parameters,
        "oos_report": {
            **oos_metrics,
            "pnl_by_hour": _parse_bucket(oos_metrics["pnl_by_hour"]),
            "pnl_by_regime": _parse_bucket(oos_metrics["pnl_by_regime"]),
        },
        "fee_stress_report": {
            "baseline_oos_net_pnl": oos_metrics["net_pnl"],
            "stressed_oos_net_pnl": fee_metrics["net_pnl"],
            "delta": fee_metrics["net_pnl"] - oos_metrics["net_pnl"],
            "stressed_fee_bps": fee_stress_cost.fee_bps,
        },
        "slippage_stress_report": {
            "baseline_oos_net_pnl": oos_metrics["net_pnl"],
            "stressed_oos_net_pnl": slip_metrics["net_pnl"],
            "delta": slip_metrics["net_pnl"] - oos_metrics["net_pnl"],
            "stressed_slippage_bps": slip_stress_cost.slippage_bps,
        },
        "parameter_perturbation_report": _perturbation_report(splits, fam, base_cost),
        "pnl_by_hour": _parse_bucket(oos_metrics["pnl_by_hour"]),
        "pnl_by_regime": _parse_bucket(oos_metrics["pnl_by_regime"]),
        "equity_curve": _equity_curve(oos_trades),
        "robustness_snapshot": robust,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run deep-dive workflows for shortlisted candidate families")
    parser.add_argument("--csv", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=Path("outputs"))
    parser.add_argument("--n-families", type=int, default=120)
    parser.add_argument("--min-trades", type=int, default=20)
    parser.add_argument("--min-trades-alt", type=int, default=30)
    parser.add_argument("--sample-rows", type=int, default=50000)
    parser.add_argument("--build-sample-if-missing", action="store_true")
    args = parser.parse_args()

    if args.build_sample_if_missing:
        maybe_make_sample(args.csv, rows=args.sample_rows)

    args.output_dir.mkdir(parents=True, exist_ok=True)

    data = prepare_features(_read_csv_rows(args.csv))
    splits = split_dataset(data)
    families = generate_strategy_families(args.n_families)
    fam_lookup = {f.family_id: f for f in families}

    base_cost = CostModel(fee_bps=4.0, slippage_bps=1.5)

    backtest_rows = []
    robust_rows = []
    for fam in families:
        all_trades = []
        split_metrics = {}
        for split_name, split_rows in splits.items():
            trades, metrics = backtest_family(split_rows, fam, base_cost, split_name)
            all_trades.extend(trades)
            split_metrics[split_name] = metrics
        backtest_rows.append(
            {
                "family_id": fam.family_id,
                "family_name": fam.family_name,
                "hypothesis_class": fam.hypothesis_class,
                "train_net_pnl": split_metrics["train"]["net_pnl"],
                "validation_net_pnl": split_metrics["validation"]["net_pnl"],
                "oos_net_pnl": split_metrics["oos"]["net_pnl"],
                "oos_expectancy": split_metrics["oos"]["expectancy"],
                "oos_profit_factor": split_metrics["oos"]["profit_factor"],
                "max_drawdown": min(split_metrics["train"]["max_drawdown"], split_metrics["validation"]["max_drawdown"], split_metrics["oos"]["max_drawdown"]),
                "trade_count": len(all_trades),
            }
        )
        robust_rows.append(run_robustness_tests(splits, fam, base_cost))

    ranked_20 = rank_candidates(backtest_rows, robust_rows, min_trades=args.min_trades)
    ranked_30 = rank_candidates(backtest_rows, robust_rows, min_trades=args.min_trades_alt)

    deep_dives = {}
    for fam_id in TARGET_FAMILIES:
        fam = fam_lookup[fam_id]
        deep_dives[fam_id] = _deep_dive_for_family(fam, splits, base_cost)

    (args.output_dir / "fam_0053_deep_dive.json").write_text(json.dumps(deep_dives["FAM_0053"], indent=2), encoding="utf-8")
    (args.output_dir / "fam_0039_deep_dive.json").write_text(json.dumps(deep_dives["FAM_0039"], indent=2), encoding="utf-8")

    score_0053 = next((r["robustness_score"] for r in ranked_20 if r["family_id"] == "FAM_0053"), float("-inf"))
    score_0039 = next((r["robustness_score"] for r in ranked_20 if r["family_id"] == "FAM_0039"), float("-inf"))
    stronger = "FAM_0053" if score_0053 >= score_0039 else "FAM_0039"

    lines = [
        "# FAM Deep Dive Comparison",
        "",
        f"- Dataset rows: {len(data)}",
        f"- Ranking filter min_trades={args.min_trades}: {len(ranked_20)} candidates survive",
        f"- Ranking filter min_trades={args.min_trades_alt}: {len(ranked_30)} candidates survive",
        "",
        "## Candidate Scores (min_trades=20)",
        f"- FAM_0053 robustness_score: {score_0053:.6f}",
        f"- FAM_0039 robustness_score: {score_0039:.6f}",
        "",
        "## Deployment Recommendation",
        f"**Stronger deployment candidate: {stronger}**",
        "",
        "Decision basis: higher robustness score under the stricter trade-count discipline (min_trades=20) while both families remain in-scope for deep dive.",
    ]
    (args.output_dir / "fam_comparison.md").write_text("\n".join(lines), encoding="utf-8")

    print(f"Deep dive complete. Stronger candidate: {stronger}")


if __name__ == "__main__":
    main()
