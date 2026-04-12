from __future__ import annotations

import argparse
import csv
import glob
import html
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT))
from src.ranking import rank_candidates


def read_json(path: Path) -> Any | None:
    if not path.exists():
        return None
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def read_text(path: Path) -> str | None:
    if not path.exists():
        return None
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return None


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    try:
        with path.open("r", encoding="utf-8", newline="") as f:
            return list(csv.DictReader(f))
    except Exception:
        return []


def parse_md_value(md: str | None, label: str) -> str | None:
    if not md:
        return None
    for line in md.splitlines():
        line = line.strip()
        if line.lower().startswith(f"- {label.lower()}:"):
            return line.split(":", 1)[1].strip()
    return None


def to_float(v: Any, default: float = 0.0) -> float:
    try:
        if v is None or v == "":
            return default
        return float(v)
    except Exception:
        return default


def to_int(v: Any, default: int = 0) -> int:
    try:
        if v is None or v == "":
            return default
        return int(float(v))
    except Exception:
        return default


def fmt_num(v: Any, digits: int = 2) -> str:
    if v is None or v == "":
        return "N/A"
    f = to_float(v, default=float("nan"))
    if f != f:
        return "N/A"
    return f"{f:,.{digits}f}"


def fmt_pnl(v: Any) -> str:
    return fmt_num(v, 2)


def pnl_class(v: Any) -> str:
    return "pos" if to_float(v, 0.0) >= 0 else "neg"


def safe(s: Any) -> str:
    return html.escape("" if s is None else str(s))


def compute_trade_journal_stats(rows: list[dict[str, str]], initial_capital: float) -> dict[str, Any]:
    n = len(rows)
    if n == 0:
        return {
            "trades": 0,
            "starting_capital": initial_capital,
            "ending_equity": initial_capital,
            "win_rate": 0.0,
            "net_pnl": 0.0,
            "return_pct": 0.0,
            "max_drawdown_pct": 0.0,
            "gross_pnl": 0.0,
            "fees": 0.0,
            "slippage": 0.0,
            "avg_pnl": 0.0,
        }
    net = sum(to_float(r.get("net_pnl")) for r in rows)
    gross = sum(to_float(r.get("gross_pnl")) for r in rows)
    fees = sum(to_float(r.get("fees")) for r in rows)
    slippage = sum(to_float(r.get("slippage_cost")) for r in rows)
    wins = sum(1 for r in rows if to_float(r.get("net_pnl")) > 0)
    eq = initial_capital
    peak = initial_capital
    mdd_pct = 0.0
    for r in rows:
        eq += to_float(r.get("net_pnl"))
        peak = max(peak, eq)
        if peak > 0:
            mdd_pct = min(mdd_pct, ((eq - peak) / peak) * 100.0)
    return {
        "trades": n,
        "starting_capital": initial_capital,
        "ending_equity": initial_capital + net,
        "win_rate": wins / n,
        "net_pnl": net,
        "return_pct": (net / initial_capital * 100.0) if initial_capital else 0.0,
        "max_drawdown_pct": mdd_pct,
        "gross_pnl": gross,
        "fees": fees,
        "slippage": slippage,
        "avg_pnl": net / n if n else 0.0,
    }


def dict_items_sorted(d: dict[str, Any] | None) -> list[tuple[str, float]]:
    if not isinstance(d, dict):
        return []
    out = []
    for k, v in d.items():
        out.append((str(k), to_float(v)))
    return sorted(out, key=lambda x: x[1], reverse=True)


def parse_literal_dict(v: Any) -> dict[str, Any]:
    if isinstance(v, dict):
        return v
    if not isinstance(v, str) or not v.strip():
        return {}
    s = v.strip()
    if s.startswith("{") and s.endswith("}"):
        try:
            return json.loads(s.replace("'", '"'))
        except Exception:
            return {}
    return {}


def parse_min_trades(v: Any, default: int = 20) -> int:
    if isinstance(v, int):
        return v
    if isinstance(v, str):
        digits = "".join(ch for ch in v if ch.isdigit())
        if digits:
            return int(digits)
    return default


def normalize_backtest_rows(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for r in rows:
        out.append(
            {
                **r,
                "train_net_pnl": to_float(r.get("train_net_pnl")),
                "validation_net_pnl": to_float(r.get("validation_net_pnl")),
                "oos_net_pnl": to_float(r.get("oos_net_pnl")),
                "starting_capital": to_float(r.get("starting_capital"), 10000.0),
                "ending_equity": to_float(r.get("ending_equity")),
                "oos_return_pct": to_float(r.get("oos_return_pct")),
                "train_profit_factor": to_float(r.get("train_profit_factor")),
                "validation_profit_factor": to_float(r.get("validation_profit_factor")),
                "oos_profit_factor": to_float(r.get("oos_profit_factor")),
                "train_expectancy": to_float(r.get("train_expectancy")),
                "validation_expectancy": to_float(r.get("validation_expectancy")),
                "oos_expectancy": to_float(r.get("oos_expectancy")),
                "max_drawdown": to_float(r.get("max_drawdown")),
                "max_drawdown_pct": to_float(r.get("max_drawdown_pct")),
                "trade_count": to_int(r.get("trade_count")),
            }
        )
    return out


def normalize_robust_rows(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for r in rows:
        out.append(
            {
                **r,
                "fee_stress_pnl_delta": to_float(r.get("fee_stress_pnl_delta")),
                "slippage_stress_pnl_delta": to_float(r.get("slippage_stress_pnl_delta")),
                "parameter_stability": to_float(r.get("parameter_stability")),
                "outlier_dependence": to_float(r.get("outlier_dependence")),
                "baseline_oos_trade_count": to_int(r.get("baseline_oos_trade_count")),
            }
        )
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Build strategy factory HTML report")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "outputs")
    parser.add_argument("--out-file", type=Path, default=None)
    parser.add_argument("--initial-capital", type=float, default=10000.0)
    args = parser.parse_args()

    outputs_dir = args.output_dir
    out_file = args.out_file or (outputs_dir / "strategy_factory_report.html")

    top5_json = read_json(outputs_dir / "top5_strategies.json") or []
    top5_md = read_text(outputs_dir / "top5_strategies.md")
    sf_summary_json = read_json(outputs_dir / "strategy_factory_summary.json")
    sf_summary_md = read_text(outputs_dir / "strategy_factory_summary.md")
    backtest_rows = read_csv(outputs_dir / "family_backtest_results.csv")
    robust_rows = read_csv(outputs_dir / "family_robustness_results.csv")
    catalog_rows = read_csv(outputs_dir / "family_catalog.csv")
    failure_taxonomy = read_json(outputs_dir / "failure_taxonomy.json")
    regime_rows = read_csv(outputs_dir / "regime_survival_table.csv")
    fam_0039 = read_json(outputs_dir / "fam_0039_deep_dive.json")
    fam_0053 = read_json(outputs_dir / "fam_0053_deep_dive.json")
    fam_comparison_md = read_text(outputs_dir / "fam_comparison.md")

    available_files = []
    candidate_sources = [
        "top5_strategies.json",
        "top5_strategies.md",
        "strategy_factory_summary.json",
        "strategy_factory_summary.md",
        "family_backtest_results.csv",
        "family_robustness_results.csv",
        "family_catalog.csv",
        "failure_taxonomy.json",
        "regime_survival_table.csv",
        "fam_0039_deep_dive.json",
        "fam_0053_deep_dive.json",
        "fam_comparison.md",
    ]
    for fn in candidate_sources:
        if (outputs_dir / fn).exists():
            available_files.append(f"outputs/{fn}")

    trade_files = sorted(glob.glob(str(outputs_dir / "top5_trade_journals" / "*.csv")))
    for tf in trade_files:
        rel = Path(tf).relative_to(ROOT)
        available_files.append(str(rel).replace("\\", "/"))

    families_tested = None
    candidates_passing = None
    min_trades = None
    if isinstance(sf_summary_json, dict):
        families_tested = sf_summary_json.get("families_evaluated") or sf_summary_json.get("families_generated")
        candidates_passing = sf_summary_json.get("candidates_passing_filters")
        min_trades = sf_summary_json.get("min_trades")
    if families_tested is None:
        families_tested = parse_md_value(sf_summary_md, "Families evaluated") or parse_md_value(sf_summary_md, "Families generated")
    if candidates_passing is None:
        candidates_passing = parse_md_value(fam_comparison_md, "Ranking filter min_trades=20")
        if candidates_passing:
            try:
                candidates_passing = int(str(candidates_passing).split()[0])
            except Exception:
                pass
    if min_trades is None:
        mline = parse_md_value(fam_comparison_md, "Ranking filter min_trades=20")
        if mline:
            min_trades = 20

    numeric_backtest_rows = normalize_backtest_rows(backtest_rows)
    numeric_robust_rows = normalize_robust_rows(robust_rows)
    robust_map = {r.get("family_id", ""): r for r in numeric_robust_rows}
    backtest_map = {r.get("family_id", ""): r for r in numeric_backtest_rows}
    catalog_map = {r.get("family_id", ""): r for r in catalog_rows}

    ranking_min_trades = parse_min_trades(min_trades, default=20)
    ranked_rows = rank_candidates(numeric_backtest_rows, numeric_robust_rows, min_trades=ranking_min_trades)

    leaderboard = []
    for row in ranked_rows:
        leaderboard.append(
            {
                "family_id": row.get("family_id", ""),
                "family_name": row.get("family_name", ""),
                "robust_score": to_float(row.get("robustness_score"), 0.0),
                "parameter_stability_raw": to_float(row.get("parameter_stability"), 0.0),
                "validation_pnl": to_float(row.get("validation_net_pnl"), 0.0),
                "oos_pnl": to_float(row.get("oos_net_pnl"), 0.0),
                "trade_count": to_int(row.get("trade_count"), 0),
                "max_drawdown": to_float(row.get("max_drawdown_pct", row.get("max_drawdown")), 0.0),
                "profit_factor": to_float(row.get("oos_profit_factor"), 0.0),
                "hypothesis_class": row.get("hypothesis_class", ""),
            }
        )
    for row in leaderboard:
        source = next((r for r in ranked_rows if r.get("family_id") == row["family_id"]), None)
        assert source is not None, f"Leaderboard family {row['family_id']} missing from ranking source."
        assert abs(row["robust_score"] - to_float(source.get("robustness_score"), 0.0)) < 1e-12, (
            f"Leaderboard robust score mismatch for {row['family_id']}."
        )
    top5_cards = []
    for i, row in enumerate(leaderboard[:5], start=1):
        top5_cards.append(
            {
                "rank": i,
                "family_id": row["family_id"],
                "family_name": row["family_name"] or "N/A",
                "hypothesis_class": row["hypothesis_class"] or "N/A",
                "robust_score": row["robust_score"],
                "parameter_stability_raw": row["parameter_stability_raw"],
                "validation_pnl": row["validation_pnl"],
                "oos_pnl": row["oos_pnl"],
                "trade_count": row["trade_count"],
                "rationale": (
                    f"Robust score={row['robust_score']:.4f} (normalized ranking score), "
                    f"parameter_stability_raw={row['parameter_stability_raw']:.4f}, "
                    f"OOS pnl={row['oos_pnl']:.2f}, validation pnl={row['validation_pnl']:.2f}, trades={row['trade_count']}."
                ),
            }
        )

    top_deploy = top5_cards[0]["family_id"] if top5_cards else "N/A"
    backup = top5_cards[1]["family_id"] if len(top5_cards) > 1 else "N/A"

    expected_top5_ids = [r["family_id"] for r in leaderboard[:5]]
    cards_top5_ids = [c["family_id"] for c in top5_cards]
    assert cards_top5_ids == expected_top5_ids, "Top 5 cards must match first 5 leaderboard rows."
    leaderboard_score_map = {r["family_id"]: r["robust_score"] for r in leaderboard}
    for c in top5_cards:
        assert c["family_id"] in leaderboard_score_map, f"Card family {c['family_id']} missing from leaderboard."
        assert abs(c["robust_score"] - leaderboard_score_map[c["family_id"]]) < 1e-12, (
            f"Displayed robust score mismatch for {c['family_id']}."
        )

    top5_ids = {c["family_id"] for c in top5_cards}
    hypothesis_counts = Counter(c.get("hypothesis_class", "Unknown") for c in top5_cards)
    diversified = "Diversified" if len(hypothesis_counts) >= 4 else "Concentrated"

    deep_reco = "N/A"
    deep_reason = "No deep dive files available."
    if fam_0039 and fam_0053:
        s39 = to_float((fam_0039.get("robustness_snapshot") or {}).get("parameter_stability"))
        s53 = to_float((fam_0053.get("robustness_snapshot") or {}).get("parameter_stability"))
        deep_reco = "FAM_0039" if s39 >= s53 else "FAM_0053"
        deep_reason = f"Selected by higher perturbation stability ({fmt_num(max(s39, s53), 4)})."
    if fam_comparison_md and "Stronger deployment candidate:" in fam_comparison_md:
        for line in fam_comparison_md.splitlines():
            if "Stronger deployment candidate:" in line:
                deep_reco = line.split(":", 1)[1].replace("**", "").strip()
                deep_reason = "Based on fam_comparison.md recommendation."

    trade_summaries: list[dict[str, Any]] = []
    for tf in trade_files:
        p = Path(tf)
        rows = read_csv(p)
        stats = compute_trade_journal_stats(rows, initial_capital=args.initial_capital)
        preview = rows[:8]
        trade_summaries.append({"file": p.name, "stats": stats, "preview": preview})

    failure_items = []
    if isinstance(failure_taxonomy, dict):
        for k, v in failure_taxonomy.items():
            failure_items.append((k, to_int(v)))
        failure_items.sort(key=lambda x: x[1], reverse=True)

    regime_summary = []
    for r in regime_rows[:10]:
        d = parse_literal_dict(r.get("pnl_by_regime"))
        best = dict_items_sorted(d)[:1]
        regime_summary.append(
            {
                "family_id": r.get("family_id", ""),
                "hypothesis_class": r.get("hypothesis_class", ""),
                "best_regime": best[0][0] if best else "N/A",
                "best_regime_pnl": best[0][1] if best else 0.0,
                "robustness_score": to_float(r.get("robustness_score"), 0.0),
            }
        )

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    html_out = f"""<!doctype html>
<html lang=\"en\"> 
<head>
<meta charset=\"utf-8\" />
<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
<title>BTCUSDT Strategy Factory Report</title>
<style>
:root {{ --bg:#0b1020; --panel:#121a2d; --panel2:#17233a; --text:#e7edf8; --muted:#9aa7bd; --pos:#2ecc71; --neg:#ff6b6b; --accent:#7aa2ff; --line:#24314d; }}
*{{box-sizing:border-box}} body{{margin:0;font-family:Inter,Segoe UI,Arial,sans-serif;background:linear-gradient(180deg,#0b1020,#0d1325);color:var(--text)}}
.container{{max-width:1320px;margin:0 auto;padding:28px}}
h1,h2,h3{{margin:0 0 12px}} h1{{font-size:30px}} h2{{font-size:22px;margin-top:28px}} h3{{font-size:16px}}
.muted{{color:var(--muted)}}
.grid{{display:grid;gap:14px}} .g4{{grid-template-columns:repeat(auto-fit,minmax(220px,1fr))}} .g2{{grid-template-columns:repeat(auto-fit,minmax(340px,1fr))}}
.card{{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:16px;box-shadow:0 6px 20px rgba(0,0,0,.25)}}
.kpi{{font-size:26px;font-weight:700}} .label{{font-size:12px;text-transform:uppercase;color:var(--muted);letter-spacing:.06em}}
.table-wrap{{overflow:auto;border:1px solid var(--line);border-radius:12px}}
table{{width:100%;border-collapse:collapse;min-width:880px;background:var(--panel)}} th,td{{padding:10px 12px;border-bottom:1px solid var(--line);text-align:left;font-size:13px}}
th{{position:sticky;top:0;background:var(--panel2);cursor:pointer}} tr:hover td{{background:#141f34}}
.badge{{padding:2px 8px;border-radius:999px;background:#1e2c4a;color:#b7c8e8;font-size:11px}}
.top5{{outline:1px solid #35508c;background:#13213d}}
.pos{{color:var(--pos)}} .neg{{color:var(--neg)}}
.bar{{height:10px;background:#1f2a44;border-radius:999px;overflow:hidden}} .bar > span{{display:block;height:100%;background:linear-gradient(90deg,#578dff,#85f0ff)}}
.small{{font-size:12px}}
pre{{white-space:pre-wrap;background:#0f1729;padding:10px;border-radius:10px;border:1px solid var(--line);font-size:12px}}
footer{{margin:28px 0 8px;color:var(--muted);font-size:12px}}
</style>
</head>
<body>
<div class=\"container\">
<section class=\"card\">
  <h1>BTCUSDT Strategy Factory Report</h1>
  <div class=\"muted\">Institutional review pack · Generated {safe(timestamp)}</div>
  <div class=\"grid g4\" style=\"margin-top:16px\">
    <div class=\"card\"><div class=\"label\">Families tested</div><div class=\"kpi\">{safe(families_tested or 'data not found')}</div></div>
    <div class=\"card\"><div class=\"label\">Candidates passing filters</div><div class=\"kpi\">{safe(candidates_passing or 'data not found')}</div></div>
    <div class=\"card\"><div class=\"label\">Min trades threshold</div><div class=\"kpi\">{safe(min_trades or 'data not found')}</div></div>
    <div class=\"card\"><div class=\"label\">Starting capital (USD)</div><div class=\"kpi\">{fmt_num(args.initial_capital, 2)}</div></div>
    <div class=\"card\"><div class=\"label\">Top / Backup</div><div class=\"kpi\">{safe(top_deploy)} <span class=\"muted\">/</span> {safe(backup)}</div></div>
  </div>
  <p style=\"margin-top:14px\">Current conclusion: Prioritize <b>{safe(top_deploy)}</b> for hardening, keep <b>{safe(backup)}</b> as secondary candidate, and continue strict cost/stability stress before any live transition.</p>
</section>

<h2>Section 2 — Top 5 Candidates Overview</h2>
<div class=\"grid g2\">"""

    if top5_cards:
        for c in top5_cards:
            html_out += f"""
<div class=\"card\">
  <div style=\"display:flex;justify-content:space-between;gap:8px\"><h3>#{c['rank']} {safe(c['family_id'])}</h3><span class=\"badge\">{safe(c['hypothesis_class'])}</span></div>
  <div class=\"small muted\">{safe(c['family_name'])}</div>
  <div class=\"grid g4\" style=\"margin-top:10px\">
    <div><div class=\"label\">Robust score (normalized)</div><div>{fmt_num(c['robust_score'],4)}</div></div>
    <div><div class=\"label\">Parameter stability (raw)</div><div>{fmt_num(c['parameter_stability_raw'],4)}</div></div>
    <div><div class=\"label\">Validation PnL</div><div class=\"{pnl_class(c['validation_pnl'])}\">{fmt_pnl(c['validation_pnl'])}</div></div>
    <div><div class=\"label\">OOS PnL</div><div class=\"{pnl_class(c['oos_pnl'])}\">{fmt_pnl(c['oos_pnl'])}</div></div>
    <div><div class=\"label\">Trade count</div><div>{c['trade_count']}</div></div>
  </div>
  <p class=\"small\" style=\"margin-top:10px\">{safe(c['rationale'])}</p>
</div>
"""
    else:
        html_out += "<div class='card'>data not found</div>"

    html_out += "</div>\n<h2>Section 3 — Leaderboard Table</h2>\n"

    if leaderboard:
        html_out += """
<div class="table-wrap"><table id="leaderboard"><thead><tr>
<th onclick="sortTable(0)">family_id</th>
<th onclick="sortTable(1)">family_name</th>
<th onclick="sortTable(2)">robust_score</th>
<th onclick="sortTable(3)">validation_pnl</th>
<th onclick="sortTable(4)">oos_pnl</th>
<th onclick="sortTable(5)">trade_count</th>
<th onclick="sortTable(6)">max_drawdown_pct</th>
<th onclick="sortTable(7)">profit_factor</th>
</tr></thead><tbody>
"""
        for r in leaderboard:
            cls = "top5" if r["family_id"] in top5_ids else ""
            html_out += f"""<tr class=\"{cls}\"><td>{safe(r['family_id'])}</td><td>{safe(r['family_name'])}</td><td>{fmt_num(r['robust_score'],4)}</td><td class=\"{pnl_class(r['validation_pnl'])}\">{fmt_pnl(r['validation_pnl'])}</td><td class=\"{pnl_class(r['oos_pnl'])}\">{fmt_pnl(r['oos_pnl'])}</td><td>{r['trade_count']}</td><td class=\"{pnl_class(r['max_drawdown'])}\">{fmt_num(r['max_drawdown'],2)}%</td><td>{fmt_num(r['profit_factor'],3)}</td></tr>"""
        html_out += "</tbody></table></div>"
    else:
        html_out += "<div class='card'>data not found</div>"

    html_out += "<h2>Section 4 — Candidate Diversity</h2>"
    if hypothesis_counts:
        total = sum(hypothesis_counts.values())
        html_out += f"<div class='card'><div>Shortlist profile: <b>{diversified}</b> ({len(hypothesis_counts)} hypothesis classes represented in top 5).</div>"
        for k, v in hypothesis_counts.items():
            pct = (100.0 * v / total) if total else 0
            html_out += f"<div style='margin-top:8px'><div class='small'>{safe(k)} · {v}</div><div class='bar'><span style='width:{pct:.1f}%'></span></div></div>"
        html_out += "</div>"
    else:
        html_out += "<div class='card'>data not found</div>"

    html_out += "<h2>Section 5 — Deep Dive Comparison (FAM_0039 vs FAM_0053)</h2>"
    if fam_0039 and fam_0053:
        def deep_block(d: dict[str, Any], lbl: str) -> str:
            oos = d.get("oos_report") or {}
            fee = d.get("fee_stress_report") or {}
            slip = d.get("slippage_stress_report") or {}
            pert = d.get("parameter_perturbation_report") or []
            reg = dict_items_sorted(d.get("pnl_by_regime") or oos.get("pnl_by_regime") or {})[:4]
            hour = dict_items_sorted(d.get("pnl_by_hour") or oos.get("pnl_by_hour") or {})[:5]
            return f"""
<div class='card'>
  <h3>{safe(lbl)} · {safe(d.get('family_name',''))}</h3>
  <div class='grid g4'>
    <div><div class='label'>OOS Net PnL</div><div class='{pnl_class(oos.get('net_pnl'))}'>{fmt_pnl(oos.get('net_pnl'))}</div></div>
    <div><div class='label'>Validation proxy</div><div>{fmt_num((d.get('robustness_snapshot') or {}).get('parameter_stability'),4)}</div></div>
    <div><div class='label'>Fee stress delta</div><div class='{pnl_class(fee.get('delta'))}'>{fmt_pnl(fee.get('delta'))}</div></div>
    <div><div class='label'>Slippage delta</div><div class='{pnl_class(slip.get('delta'))}'>{fmt_pnl(slip.get('delta'))}</div></div>
  </div>
  <div class='small' style='margin-top:8px'>Perturbation stability scenarios: {len(pert)}</div>
  <div class='small' style='margin-top:8px'><b>PnL by hour (top):</b> {safe(', '.join([f'{k}:{fmt_num(v,0)}' for k,v in hour]) or 'N/A')}</div>
  <div class='small' style='margin-top:4px'><b>PnL by regime:</b> {safe(', '.join([f'{k}:{fmt_num(v,0)}' for k,v in reg]) or 'N/A')}</div>
</div>"""

        html_out += f"<div class='grid g2'>{deep_block(fam_0039, 'FAM_0039')}{deep_block(fam_0053, 'FAM_0053')}</div>"
        html_out += f"<div class='card' style='margin-top:12px'><b>Stronger deployment candidate: {safe(deep_reco)}</b><br><span class='small muted'>{safe(deep_reason)}</span></div>"
    else:
        html_out += "<div class='card'>data not found</div>"

    html_out += "<h2>Section 6 — Trade Journal Snapshots</h2>"
    if trade_summaries:
        for t in trade_summaries:
            s = t["stats"]
            html_out += f"""
<div class='card'>
  <h3>{safe(t['file'])}</h3>
  <div class='grid g4'>
    <div><div class='label'>Trades</div><div>{s['trades']}</div></div>
    <div><div class='label'>Starting Capital</div><div>{fmt_pnl(s['starting_capital'])}</div></div>
    <div><div class='label'>Ending Equity</div><div class='{pnl_class(s['net_pnl'])}'>{fmt_pnl(s['ending_equity'])}</div></div>
    <div><div class='label'>Win rate</div><div>{s['win_rate']*100:.2f}%</div></div>
    <div><div class='label'>Net PnL</div><div class='{pnl_class(s['net_pnl'])}'>{fmt_pnl(s['net_pnl'])}</div></div>
    <div><div class='label'>Return %</div><div class='{pnl_class(s['return_pct'])}'>{fmt_num(s['return_pct'],2)}%</div></div>
    <div><div class='label'>Max DD %</div><div class='{pnl_class(s['max_drawdown_pct'])}'>{fmt_num(s['max_drawdown_pct'],2)}%</div></div>
    <div><div class='label'>Gross PnL</div><div class='{pnl_class(s['gross_pnl'])}'>{fmt_pnl(s['gross_pnl'])}</div></div>
    <div><div class='label'>Fees</div><div class='{pnl_class(-s['fees'])}'>{fmt_pnl(s['fees'])}</div></div>
    <div><div class='label'>Slippage</div><div class='{pnl_class(-s['slippage'])}'>{fmt_pnl(s['slippage'])}</div></div>
    <div><div class='label'>Avg PnL/trade</div><div class='{pnl_class(s['avg_pnl'])}'>{fmt_pnl(s['avg_pnl'])}</div></div>
  </div>
  <div class='table-wrap' style='margin-top:10px'><table><thead><tr><th>entry</th><th>exit</th><th>side</th><th>net_pnl</th><th>fees</th><th>regime</th></tr></thead><tbody>
"""
            for r in t["preview"][:5]:
                rg = f"{r.get('trend_regime','')}/{r.get('vol_regime','')}"
                html_out += f"<tr><td>{safe(r.get('timestamp_entry'))}</td><td>{safe(r.get('timestamp_exit'))}</td><td>{safe(r.get('side'))}</td><td class='{pnl_class(r.get('net_pnl'))}'>{fmt_pnl(r.get('net_pnl'))}</td><td>{fmt_pnl(r.get('fees'))}</td><td>{safe(rg)}</td></tr>"
            html_out += "</tbody></table></div></div>"
    else:
        html_out += "<div class='card'>data not found</div>"

    html_out += "<h2>Section 7 — Failure Taxonomy</h2>"
    if failure_items:
        html_out += "<div class='card'>"
        total_fails = sum(v for _, v in failure_items) or 1
        for k, v in failure_items:
            pct = 100 * v / total_fails
            html_out += f"<div style='margin-top:8px'><div class='small'>{safe(k)} · {v}</div><div class='bar'><span style='width:{pct:.1f}%'></span></div></div>"
        html_out += "<p class='small' style='margin-top:10px'>Most frequent failure modes are shown above. Cross-class failure analysis can be expanded by joining taxonomy labels with hypothesis_class in future runs.</p></div>"
    else:
        html_out += "<div class='card'>data not found</div>"

    html_out += "<h2>Section 8 — Regime Survival</h2>"
    if regime_summary:
        html_out += "<div class='table-wrap'><table><thead><tr><th>family_id</th><th>hypothesis_class</th><th>best regime</th><th>best regime pnl</th><th>robustness_score</th></tr></thead><tbody>"
        for r in regime_summary:
            html_out += f"<tr><td>{safe(r['family_id'])}</td><td>{safe(r['hypothesis_class'])}</td><td>{safe(r['best_regime'])}</td><td class='{pnl_class(r['best_regime_pnl'])}'>{fmt_pnl(r['best_regime_pnl'])}</td><td>{fmt_num(r['robustness_score'],4)}</td></tr>"
        html_out += "</tbody></table></div>"
    else:
        html_out += "<div class='card'>data not found</div>"

    html_out += """
<h2>Section 9 — Key Risks</h2>
<div class="card"><ul>
<li>These are research candidates, not live-ready strategies.</li>
<li>Performance may be sample-dependent and regime-dependent.</li>
<li>Execution costs (fees/slippage/latency) remain critical to viability.</li>
<li>Forward paper-trading and stricter walk-forward validation are still required.</li>
</ul></div>

<h2>Section 10 — Recommended Next Actions</h2>
<div class="card"><ol>
<li>Further harden the leading candidate with stricter parameter perturbation tests.</li>
<li>Extend out-of-sample testing window across additional market regimes.</li>
<li>Add month-by-month validation and stability monitoring gates.</li>
<li>Apply higher fee/slippage stress assumptions and re-rank.</li>
<li>Run forward paper trading with production-like execution constraints.</li>
<li>Allow live deployment only after passing stricter risk and robustness checks.</li>
</ol></div>

<section class="card" style="margin-top:24px">
<h3>Data Sources Found</h3>
<pre>""" + "\n".join(safe(f) for f in available_files) + """</pre>
</section>

<footer>Self-contained local HTML report. No CDN dependencies.</footer>
</div>
<script>
function sortTable(n){
  const table=document.getElementById('leaderboard'); if(!table) return;
  let switching=true, dir='desc', switchcount=0;
  while(switching){
    switching=false; const rows=table.rows;
    for(let i=1;i<rows.length-1;i++){
      let shouldSwitch=false;
      let x=rows[i].getElementsByTagName('TD')[n];
      let y=rows[i+1].getElementsByTagName('TD')[n];
      let xv=parseFloat(x.textContent.replace(/,/g,''));
      let yv=parseFloat(y.textContent.replace(/,/g,''));
      if(isNaN(xv)||isNaN(yv)){xv=x.textContent.toLowerCase(); yv=y.textContent.toLowerCase();}
      if((dir==='asc' && xv>yv) || (dir==='desc' && xv<yv)){shouldSwitch=true; break;}
    }
    if(shouldSwitch){rows[i].parentNode.insertBefore(rows[i+1],rows[i]); switching=true; switchcount++;}
    else if(switchcount===0&&dir==='desc'){dir='asc'; switching=true;}
  }
}
</script>
</body></html>
"""

    outputs_dir.mkdir(parents=True, exist_ok=True)
    out_file.write_text(html_out, encoding="utf-8")
    print(str(out_file.as_posix()))
    print("USED_SOURCES:")
    for src in available_files:
        print(src)


if __name__ == "__main__":
    main()
