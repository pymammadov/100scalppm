from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any

from .family_definitions import StrategyFamily
from .family_evaluator import CostModel, DEFAULT_INITIAL_CAPITAL, backtest_family, prepare_features, split_dataset
from .family_generator import generate_strategy_families
from .ranking import rank_candidates
from .reporting import write_catalog, write_csv, write_summary, write_top5_artifacts
from .robustness import run_robustness_tests

REQUIRED_COLUMNS = {"timestamp", "open", "high", "low", "close", "volume"}


def _read_csv_rows(csv_path: Path) -> list[dict[str, Any]]:
    rows = []
    with csv_path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        missing = REQUIRED_COLUMNS - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"Missing required columns: {sorted(missing)}")
        for r in reader:
            rows.append(
                {
                    "timestamp": r["timestamp"],
                    "open": float(r["open"]),
                    "high": float(r["high"]),
                    "low": float(r["low"]),
                    "close": float(r["close"]),
                    "volume": float(r["volume"]),
                }
            )
    return rows


def run_strategy_factory(
    csv_path: Path,
    n_families: int,
    output_dir: Path,
    min_trades: int = 20,
    initial_capital: float = DEFAULT_INITIAL_CAPITAL,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "top5_trade_journals").mkdir(parents=True, exist_ok=True)
    (output_dir / "top5_equity_curves").mkdir(parents=True, exist_ok=True)
    for folder in [output_dir / "top5_trade_journals", output_dir / "top5_equity_curves"]:
        for file in folder.glob("*"):
            if file.is_file():
                file.unlink()

    data = prepare_features(_read_csv_rows(csv_path))
    splits = split_dataset(data)
    families = generate_strategy_families(n_families)
    family_lookup: dict[str, StrategyFamily] = {f.family_id: f for f in families}
    write_catalog(families, output_dir)

    base_cost = CostModel(fee_bps=4.0, slippage_bps=1.5)
    backtest_rows: list[dict[str, Any]] = []
    robust_rows: list[dict[str, Any]] = []
    journals_top_source: dict[str, list[dict[str, Any]]] = {}
    failure_counts = {"too_few_trades": 0, "empty_oos": 0, "evaluation_error": 0}

    for fam in families:
        try:
            split_metrics: dict[str, dict[str, Any]] = {}
            split_trades: dict[str, list[dict[str, Any]]] = {}
            for split_name, split_rows in splits.items():
                trades, metrics = backtest_family(split_rows, fam, base_cost, split_name, initial_capital=initial_capital)
                split_trades[split_name] = trades
                split_metrics[split_name] = metrics
            all_trades = split_trades["train"] + split_trades["validation"] + split_trades["oos"]
            if split_metrics["oos"]["trade_count"] == 0:
                failure_counts["empty_oos"] += 1
            if len(all_trades) < 25:
                failure_counts["too_few_trades"] += 1

            no_cost_oos, no_cost_m = backtest_family(
                splits["oos"], fam, CostModel(fee_bps=0.0, slippage_bps=0.0), "oos_nocost", initial_capital=initial_capital
            )
            row = {
                "family_id": fam.family_id,
                "family_name": fam.family_name,
                "hypothesis_class": fam.hypothesis_class,
                "initial_capital_usd": initial_capital,
                "risk_per_trade_pct": fam.parameters.get("risk_per_trade", 0.0) * 100.0,
                "max_leverage": 2.0,
                "sizing_model": "equity-based",
                "starting_capital": split_metrics["oos"]["starting_capital"],
                "ending_equity": split_metrics["oos"]["ending_equity"],
                "train_net_pnl": split_metrics["train"]["net_pnl"],
                "validation_net_pnl": split_metrics["validation"]["net_pnl"],
                "oos_net_pnl": split_metrics["oos"]["net_pnl"],
                "train_return_pct": split_metrics["train"]["return_pct"],
                "validation_return_pct": split_metrics["validation"]["return_pct"],
                "oos_return_pct": split_metrics["oos"]["return_pct"],
                "train_profit_factor": split_metrics["train"]["profit_factor"],
                "validation_profit_factor": split_metrics["validation"]["profit_factor"],
                "oos_profit_factor": split_metrics["oos"]["profit_factor"],
                "train_expectancy": split_metrics["train"]["expectancy"],
                "validation_expectancy": split_metrics["validation"]["expectancy"],
                "oos_expectancy": split_metrics["oos"]["expectancy"],
                "max_drawdown": min(split_metrics["train"]["max_drawdown"], split_metrics["validation"]["max_drawdown"], split_metrics["oos"]["max_drawdown"]),
                "max_drawdown_pct": min(
                    split_metrics["train"]["max_drawdown_pct"],
                    split_metrics["validation"]["max_drawdown_pct"],
                    split_metrics["oos"]["max_drawdown_pct"],
                ),
                "trade_count": len(all_trades),
                "average_trade_pnl": (sum(t["net_pnl"] for t in all_trades) / len(all_trades)) if all_trades else 0.0,
                "average_win": (sum(t["net_pnl"] for t in all_trades if t["net_pnl"] > 0) / max(1, len([t for t in all_trades if t["net_pnl"] > 0])) if all_trades else 0.0),
                "average_loss": (sum(t["net_pnl"] for t in all_trades if t["net_pnl"] < 0) / max(1, len([t for t in all_trades if t["net_pnl"] < 0])) if all_trades else 0.0),
                "win_rate": (len([t for t in all_trades if t["net_pnl"] > 0]) / len(all_trades)) if all_trades else 0.0,
                "cost_impact": no_cost_m["net_pnl"] - split_metrics["oos"]["net_pnl"],
                "slippage_impact": (sum(t["slippage_cost"] for t in no_cost_oos) - sum(t["slippage_cost"] for t in split_trades["oos"])) if split_trades["oos"] else 0.0,
                "no_cost_result": no_cost_m["net_pnl"],
                "realistic_cost_result": split_metrics["oos"]["net_pnl"],
                "average_holding_time": split_metrics["oos"]["average_holding_time"],
                "average_entry_notional": split_metrics["oos"]["average_entry_notional"],
                "max_entry_notional": split_metrics["oos"]["max_entry_notional"],
                "average_leverage_used": split_metrics["oos"]["average_leverage_used"],
                "max_leverage_used": split_metrics["oos"]["max_leverage_used"],
                "pnl_by_side": split_metrics["oos"]["pnl_by_side"],
                "pnl_by_setup": split_metrics["oos"]["pnl_by_setup"],
                "pnl_by_hour": split_metrics["oos"]["pnl_by_hour"],
                "pnl_by_regime": split_metrics["oos"]["pnl_by_regime"],
            }
            backtest_rows.append(row)
            robust_rows.append(run_robustness_tests(splits, fam, base_cost, initial_capital=initial_capital))
            journals_top_source[fam.family_id] = split_trades["oos"]
        except Exception:
            failure_counts["evaluation_error"] += 1

    write_csv(output_dir / "family_backtest_results.csv", backtest_rows)
    write_csv(output_dir / "family_robustness_results.csv", robust_rows)
    ranked = rank_candidates(backtest_rows, robust_rows, min_trades=min_trades)
    top5 = write_top5_artifacts(ranked, family_lookup, journals_top_source, output_dir, initial_capital=initial_capital)

    (output_dir / "failure_taxonomy.json").write_text(json.dumps(failure_counts, indent=2), encoding="utf-8")
    regime_survival = [{"family_id": r["family_id"], "hypothesis_class": r["hypothesis_class"], "pnl_by_regime": r["pnl_by_regime"], "robustness_score": r["robustness_score"]} for r in ranked[:20]]
    write_summary(
        output_dir=output_dir,
        n_generated=len(families),
        n_evaluated=len(backtest_rows),
        class_counts=dict(Counter(f.hypothesis_class for f in families)),
        failure_counts=failure_counts,
        regime_survival=regime_survival,
        initial_capital=initial_capital,
        min_trades=min_trades,
        candidates_passing_filters=len(ranked),
    )
    return {"n_generated": len(families), "n_evaluated": len(backtest_rows), "top5": top5, "ranked": ranked}
