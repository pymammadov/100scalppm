from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from .family_definitions import StrategyFamily


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    headers = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=headers)
        w.writeheader()
        w.writerows(rows)


def write_catalog(families: list[StrategyFamily], output_dir: Path) -> Path:
    rows = [f.as_catalog_row() for f in families]
    path = output_dir / "family_catalog.csv"
    write_csv(path, rows)
    return path


def _equity_svg(trades: list[dict[str, Any]], out_path: Path, initial_capital: float) -> None:
    eq = []
    c = initial_capital
    for t in trades:
        c += t["net_pnl"]
        eq.append(c)
    if not eq:
        eq = [initial_capital]
    w, h = 800, 300
    minv, maxv = min(eq), max(eq)
    rng = (maxv - minv) or 1.0
    pts = []
    for i, v in enumerate(eq):
        x = 20 + (w - 40) * (i / max(1, len(eq) - 1))
        y = h - 20 - (h - 40) * ((v - minv) / rng)
        pts.append(f"{x:.2f},{y:.2f}")
    svg = f"<svg xmlns='http://www.w3.org/2000/svg' width='{w}' height='{h}'><polyline fill='none' stroke='blue' stroke-width='2' points='{' '.join(pts)}'/></svg>"
    out_path.write_text(svg, encoding="utf-8")


def write_top5_artifacts(
    ranked: list[dict[str, Any]],
    family_lookup: dict[str, StrategyFamily],
    journals: dict[str, list[dict[str, Any]]],
    output_dir: Path,
    initial_capital: float,
) -> list[dict[str, Any]]:
    top5 = ranked[:5]
    records = []
    for row in top5:
        fam = family_lookup[row["family_id"]]
        rationale = (
            f"Robust score={row['robustness_score']:.4f}, OOS pnl={row['oos_net_pnl']:.2f}, "
            f"OOS return={row.get('oos_return_pct', 0.0):.2f}%, validation pnl={row['validation_net_pnl']:.2f}, "
            f"trades={int(row['trade_count'])}, max lev={row.get('max_leverage_used', 0.0):.2f}x."
        )
        rec = {
            "family_id": fam.family_id,
            "family_name": fam.family_name,
            "hypothesis_class": fam.hypothesis_class,
            "rule_summary": fam.rule_summary,
            "parameters": fam.parameters,
            "rationale": rationale,
        }
        records.append(rec)
        t = journals.get(fam.family_id, [])
        if t:
            write_csv(output_dir / "top5_trade_journals" / f"{fam.family_id}.csv", t)
            _equity_svg(t, output_dir / "top5_equity_curves" / f"{fam.family_id}.svg", initial_capital=initial_capital)

    (output_dir / "top5_strategies.json").write_text(json.dumps(records, indent=2), encoding="utf-8")
    lines = ["# Top 5 Robust Strategies", ""]
    for i, rec in enumerate(records, 1):
        lines += [f"## {i}. {rec['family_id']} ({rec['hypothesis_class']})", f"- Name: {rec['family_name']}", f"- Rules: {rec['rule_summary']}", f"- Rationale: {rec['rationale']}", ""]
    (output_dir / "top5_strategies.md").write_text("\n".join(lines), encoding="utf-8")
    return records


def write_summary(
    output_dir: Path,
    n_generated: int,
    n_evaluated: int,
    class_counts: dict[str, int],
    failure_counts: dict[str, int],
    regime_survival: list[dict[str, Any]],
    initial_capital: float,
    min_trades: int | None = None,
    candidates_passing_filters: int | None = None,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Strategy Factory Summary",
        f"- Families generated: {n_generated}",
        f"- Families evaluated: {n_evaluated}",
        f"- Initial capital (USD): {initial_capital:.2f}",
        "- Hypothesis classes explored:",
    ]
    for k, v in class_counts.items():
        lines.append(f"  - {k}: {v}")
    lines.append("- Failure taxonomy:")
    for k, v in failure_counts.items():
        lines.append(f"  - {k}: {v}")
    (output_dir / "strategy_factory_summary.md").write_text("\n".join(lines), encoding="utf-8")
    summary_payload = {
        "families_generated": n_generated,
        "families_evaluated": n_evaluated,
        "initial_capital_usd": initial_capital,
        "hypothesis_class_counts": class_counts,
        "failure_taxonomy": failure_counts,
        "min_trades": min_trades,
        "candidates_passing_filters": candidates_passing_filters,
    }
    (output_dir / "strategy_factory_summary.json").write_text(json.dumps(summary_payload, indent=2), encoding="utf-8")
    write_csv(output_dir / "regime_survival_table.csv", regime_survival)
