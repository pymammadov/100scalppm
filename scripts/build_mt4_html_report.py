from __future__ import annotations

import argparse
import csv
import glob
import html
import json
import math
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT))
from src.ranking import rank_candidates


def read_json(path: Path) -> Any:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
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


def safe(v: Any) -> str:
    return html.escape("" if v is None else str(v))


def fmt_num(v: Any, digits: int = 2, suffix: str = "") -> str:
    if v is None or v == "":
        return "N/A"
    f = to_float(v, default=float("nan"))
    if f != f:
        return "N/A"
    return f"{f:,.{digits}f}{suffix}"


def fmt_pct(v: Any, digits: int = 2) -> str:
    return fmt_num(v, digits, "%")


def parse_dt(row: dict[str, str], key_candidates: list[str]) -> datetime | None:
    value = None
    for key in key_candidates:
        if row.get(key):
            value = row[key]
            break
    if not value:
        return None
    value = str(value).strip()
    patterns = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%d",
    ]
    for p in patterns:
        try:
            dt = datetime.strptime(value[:19], p)
            return dt.replace(tzinfo=timezone.utc)
        except Exception:
            continue
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except Exception:
        return None


def normalize_rows(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    out = []
    for r in rows:
        out.append(
            {
                **r,
                "family_id": r.get("family_id", ""),
                "family_name": r.get("family_name", ""),
                "oos_net_pnl": to_float(r.get("oos_net_pnl")),
                "oos_profit_factor": to_float(r.get("oos_profit_factor")),
                "max_drawdown": to_float(r.get("max_drawdown")),
                "max_drawdown_pct": to_float(r.get("max_drawdown_pct")),
                "trade_count": to_int(r.get("trade_count")),
                "oos_return_pct": to_float(r.get("oos_return_pct")),
            }
        )
    return out


def _should_coerce_key(key: str) -> bool:
    k = key.lower()
    numeric_tokens = (
        "pnl",
        "profit",
        "expect",
        "drawdown",
        "dd",
        "count",
        "trades",
        "trade_count",
        "factor",
        "score",
        "return",
        "fee",
        "slip",
        "stability",
        "dependence",
        "duration",
        "price",
    )
    return any(token in k for token in numeric_tokens)


def coerce_numeric_fields(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in rows:
        coerced: dict[str, Any] = dict(row)
        for key, value in row.items():
            if _should_coerce_key(key):
                if "count" in key.lower() or "trades" in key.lower():
                    coerced[key] = to_int(value)
                else:
                    coerced[key] = to_float(value)
        out.append(coerced)
    return out


def parse_family_id_from_filename(name: str) -> str | None:
    m = re.search(r"(fam[_-]?\d{4})", name.lower())
    if not m:
        return None
    return m.group(1).replace("-", "_").upper()


def winning_rate(rows: list[dict[str, Any]], side: str) -> float:
    side_rows = [r for r in rows if str(r.get("side", "")).lower().startswith(side)]
    if not side_rows:
        return 0.0
    wins = sum(1 for r in side_rows if to_float(r.get("net_pnl")) > 0)
    return 100.0 * wins / len(side_rows)


def build_trade_metrics(rows: list[dict[str, Any]], start_capital: float) -> dict[str, Any]:
    if not rows:
        return {
            "starting_capital": start_capital,
            "ending_equity": start_capital,
            "total_return_pct": 0.0,
            "period": "N/A",
            "metrics": {},
            "equity_points": [start_capital],
            "dd_points": [0.0],
            "monthly": [],
            "pnl_values": [],
            "holding_mins": [],
            "hourly": {},
            "regime": {},
        }

    pnls = [to_float(r.get("net_pnl")) for r in rows]
    gross_profit = sum(p for p in pnls if p > 0)
    gross_loss = sum(p for p in pnls if p < 0)
    net_profit = gross_profit + gross_loss
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p < 0]

    equity = start_capital
    peak = start_capital
    valley = start_capital
    max_dd_abs = 0.0
    max_dd_pct = 0.0
    eq_points = [equity]
    dd_points = [0.0]

    for p in pnls:
        equity += p
        eq_points.append(equity)
        peak = max(peak, equity)
        valley = min(valley, equity)
        dd = peak - equity
        max_dd_abs = max(max_dd_abs, dd)
        if peak > 0:
            max_dd_pct = max(max_dd_pct, (dd / peak) * 100.0)
        dd_points.append(-dd)

    abs_dd = max(0.0, start_capital - valley)
    expected = net_profit / len(pnls)
    pf = gross_profit / abs(gross_loss) if gross_loss < 0 else (999.0 if gross_profit > 0 else 0.0)
    sharpe_like = 0.0
    if len(pnls) > 1:
        mean = sum(pnls) / len(pnls)
        var = sum((x - mean) ** 2 for x in pnls) / (len(pnls) - 1)
        std = math.sqrt(var)
        if std > 0:
            sharpe_like = (mean / std) * math.sqrt(len(pnls))

    def streaks(predicate: Any) -> list[list[float]]:
        cur: list[float] = []
        all_streaks: list[list[float]] = []
        for p in pnls:
            if predicate(p):
                cur.append(p)
            else:
                if cur:
                    all_streaks.append(cur)
                cur = []
        if cur:
            all_streaks.append(cur)
        return all_streaks

    win_streaks = streaks(lambda x: x > 0)
    loss_streaks = streaks(lambda x: x < 0)

    trade_rows = []
    monthly_pnl: dict[str, float] = defaultdict(float)
    hourly: dict[int, float] = defaultdict(float)
    regime: dict[str, float] = defaultdict(float)
    holding_mins: list[float] = []

    for idx, r in enumerate(rows, start=1):
        entry_dt = parse_dt(r, ["timestamp_entry", "entry_time", "entry_ts"])
        exit_dt = parse_dt(r, ["timestamp_exit", "exit_time", "exit_ts"])
        if not exit_dt:
            exit_dt = entry_dt
        month_key = exit_dt.strftime("%Y-%m") if exit_dt else "Unknown"
        pnl = to_float(r.get("net_pnl"))
        monthly_pnl[month_key] += pnl
        if exit_dt:
            hourly[exit_dt.hour] += pnl
        trend = str(r.get("trend_regime", "")).strip() or "NA"
        vol = str(r.get("vol_regime", "")).strip() or "NA"
        regime[f"{trend}/{vol}"] += pnl
        duration = to_float(r.get("duration_min"), -1)
        if duration < 0 and entry_dt and exit_dt:
            duration = (exit_dt - entry_dt).total_seconds() / 60.0
        if duration >= 0:
            holding_mins.append(duration)

        trade_rows.append(
            {
                "trade_id": r.get("trade_id") or idx,
                "entry_time": entry_dt.strftime("%Y-%m-%d %H:%M") if entry_dt else (r.get("timestamp_entry") or "N/A"),
                "exit_time": exit_dt.strftime("%Y-%m-%d %H:%M") if exit_dt else (r.get("timestamp_exit") or "N/A"),
                "side": r.get("side", "N/A"),
                "entry_price": to_float(r.get("entry_price")),
                "exit_price": to_float(r.get("exit_price")),
                "pnl": pnl,
                "fees": to_float(r.get("fees")),
                "slippage": to_float(r.get("slippage_cost")),
                "duration": duration,
                "setup": r.get("setup_type") or r.get("setup") or "N/A",
            }
        )

    monthly = []
    running_month_equity = start_capital
    for month in sorted(monthly_pnl.keys()):
        pnl = monthly_pnl[month]
        base = running_month_equity
        ret = (pnl / base * 100.0) if base else 0.0
        running_month_equity += pnl
        monthly.append({"month": month, "pnl": pnl, "return_pct": ret})

    metrics = {
        "Total Net Profit": net_profit,
        "Gross Profit": gross_profit,
        "Gross Loss": gross_loss,
        "Profit Factor": pf,
        "Expected Payoff": expected,
        "Absolute Drawdown": abs_dd,
        "Maximal Drawdown": max_dd_abs,
        "Relative Drawdown": max_dd_pct,
        "Recovery Factor": (net_profit / max_dd_abs) if max_dd_abs > 0 else 0.0,
        "Sharpe-like Ratio": sharpe_like,
        "Total Trades": len(rows),
        "Short positions won (%)": winning_rate(rows, "s"),
        "Long positions won (%)": winning_rate(rows, "l"),
        "Profit trades (% of total)": (len(wins) / len(rows)) * 100.0,
        "Loss trades (% of total)": (len(losses) / len(rows)) * 100.0,
        "Largest profit trade": max(wins) if wins else 0.0,
        "Largest loss trade": min(losses) if losses else 0.0,
        "Average profit trade": (sum(wins) / len(wins)) if wins else 0.0,
        "Average loss trade": (sum(losses) / len(losses)) if losses else 0.0,
        "Maximum consecutive wins": max((len(s) for s in win_streaks), default=0),
        "Maximum consecutive losses": max((len(s) for s in loss_streaks), default=0),
        "Max consecutive profit": max((sum(s) for s in win_streaks), default=0.0),
        "Max consecutive loss": min((sum(s) for s in loss_streaks), default=0.0),
        "Average consecutive wins": (sum(len(s) for s in win_streaks) / len(win_streaks)) if win_streaks else 0.0,
        "Average consecutive losses": (sum(len(s) for s in loss_streaks) / len(loss_streaks)) if loss_streaks else 0.0,
    }

    first_entry = parse_dt(rows[0], ["timestamp_entry", "entry_time", "entry_ts"])
    last_exit = parse_dt(rows[-1], ["timestamp_exit", "exit_time", "exit_ts"])
    period = "N/A"
    if first_entry and last_exit:
        period = f"{first_entry.strftime('%Y-%m-%d')} to {last_exit.strftime('%Y-%m-%d')}"

    return {
        "starting_capital": start_capital,
        "ending_equity": start_capital + net_profit,
        "total_return_pct": (net_profit / start_capital * 100.0) if start_capital else 0.0,
        "period": period,
        "metrics": metrics,
        "equity_points": eq_points,
        "dd_points": dd_points,
        "monthly": monthly,
        "pnl_values": pnls,
        "holding_mins": holding_mins,
        "hourly": {str(k): v for k, v in sorted(hourly.items())},
        "regime": dict(sorted(regime.items(), key=lambda x: x[1], reverse=True)[:12]),
        "trade_rows": trade_rows,
    }


def recompute_candidate_metrics_from_journal(
    family_id: str,
    journals_by_fam: dict[str, list[dict[str, Any]]],
    start_capital: float,
) -> dict[str, Any]:
    journal_rows = journals_by_fam.get(family_id, [])
    if not journal_rows:
        raise FileNotFoundError(
            f"Missing journal for candidate {family_id}. "
            "SECTION 6 requires per-candidate journal data from outputs/top5_trade_journals."
        )

    trade_metrics = build_trade_metrics(journal_rows, start_capital)
    metrics = trade_metrics["metrics"]
    total_net_profit = to_float(metrics.get("Total Net Profit"))
    total_trades = to_int(metrics.get("Total Trades"))
    win_rate_pct = to_float(metrics.get("Profit trades (% of total)"))
    profit_factor = to_float(metrics.get("Profit Factor"))
    drawdown_pct = to_float(metrics.get("Relative Drawdown"))
    return_pct = (total_net_profit / start_capital * 100.0) if start_capital else 0.0

    if total_trades != len(journal_rows):
        raise AssertionError(
            f"Candidate {family_id} total_trades mismatch: "
            f"metrics={total_trades}, journal_rows={len(journal_rows)}"
        )
    if total_net_profit > 0 and win_rate_pct == 0.0:
        raise AssertionError(
            f"Candidate {family_id} has positive net profit ({total_net_profit}) "
            "but zero win rate; SECTION 6 metrics must match journal truth."
        )

    return {
        "family_id": family_id,
        "total_net_profit": total_net_profit,
        "profit_factor": profit_factor,
        "drawdown_pct": drawdown_pct,
        "total_trades": total_trades,
        "return_pct": return_pct,
        "win_rate_pct": win_rate_pct,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build MT4-style HTML report")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "outputs")
    parser.add_argument("--out-file", type=Path, default=None)
    parser.add_argument("--initial-capital", type=float, default=10000.0)
    args = parser.parse_args()

    out_dir = args.output_dir
    out_file = args.out_file or (out_dir / "mt4_style_report.html")

    backtest_rows = coerce_numeric_fields(normalize_rows(read_csv(out_dir / "family_backtest_results.csv")))
    robust_rows = coerce_numeric_fields(read_csv(out_dir / "family_robustness_results.csv"))
    top5_json = read_json(out_dir / "top5_strategies.json") or []
    if isinstance(top5_json, list):
        top5_json = coerce_numeric_fields(top5_json)

    ranked = rank_candidates(backtest_rows, robust_rows, min_trades=20) if backtest_rows else []
    top5_ranked = ranked[:5] if ranked else backtest_rows[:5]

    top_candidate_id = ""
    if top5_ranked:
        top_candidate_id = str(top5_ranked[0].get("family_id", ""))
    elif isinstance(top5_json, list) and top5_json:
        top_candidate_id = str(top5_json[0].get("family_id", ""))

    trade_files = sorted(glob.glob(str(out_dir / "top5_trade_journals" / "*.csv")))
    journals_by_fam: dict[str, list[dict[str, str]]] = {}
    for tf in trade_files:
        fam = parse_family_id_from_filename(Path(tf).name)
        if fam:
            journals_by_fam[fam] = coerce_numeric_fields(read_csv(Path(tf)))

    selected_journal = journals_by_fam.get(top_candidate_id, [])
    if top_candidate_id and not selected_journal:
        raise FileNotFoundError(
            f"Missing selected candidate journal for {top_candidate_id}. "
            "Cannot build report with mixed/missing SECTION 6 scope."
        )

    trade_metrics = build_trade_metrics(selected_journal, args.initial_capital)
    top5_view = []
    seen_family_ids: set[str] = set()
    for r in top5_ranked:
        fid = str(r.get("family_id", ""))
        if not fid or fid in seen_family_ids:
            continue
        seen_family_ids.add(fid)
        top5_view.append(recompute_candidate_metrics_from_journal(fid, journals_by_fam, args.initial_capital))

    symbol = "BTCUSDT"
    timeframe = "N/A"
    if selected_journal:
        timeframe = selected_journal[0].get("timeframe") or "N/A"

    title = f"{symbol} Strategy Tester Report (MT4 Style)"
    gen_ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    html_out = f"""<!doctype html>
<html><head><meta charset='utf-8'/><meta name='viewport' content='width=device-width, initial-scale=1' />
<title>{safe(title)}</title>
<style>
body {{ font-family: Tahoma, Arial, sans-serif; margin: 14px; color: #111; background: #f6f6f6; }}
.report {{ background: #fff; border: 1px solid #b9b9b9; padding: 10px 12px; }}
h1 {{ font-size: 20px; margin: 0 0 8px; }}
h2 {{ font-size: 14px; margin: 16px 0 8px; border-bottom: 1px solid #cfcfcf; padding-bottom: 3px; }}
.grid2 {{ display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }}
.tbl {{ width: 100%; border-collapse: collapse; font-size: 12px; }}
.tbl th, .tbl td {{ border: 1px solid #c9c9c9; padding: 4px 6px; }}
.tbl th {{ background: #efefef; text-align: left; }}
.val-pos {{ color: #0a7a13; }} .val-neg {{ color: #b00020; }}
.small {{ font-size: 11px; color: #555; }}
.chart-wrap {{ border:1px solid #c9c9c9; background: #fcfcfc; padding: 8px; }}
#trade-table-wrap {{ max-height: 360px; overflow: auto; }}
@media print {{ body {{ background: #fff; margin: 0; }} .report {{ border: none; }} }}
</style></head>
<body><div class='report'>
<h1>{safe(title)}</h1>
<div class='small'>Generated: {safe(gen_ts)}</div>

<h2>SECTION 1 — REPORT HEADER</h2>
<table class='tbl'>
<tr><th>Symbol</th><td>{safe(symbol)}</td><th>Timeframe</th><td>{safe(timeframe)}</td></tr>
<tr><th>Period tested</th><td>{safe(trade_metrics['period'])}</td><th>Candidate</th><td>{safe(top_candidate_id or 'N/A')}</td></tr>
<tr><th>Starting capital</th><td>{fmt_num(trade_metrics['starting_capital'],2)}</td><th>Ending equity</th><td>{fmt_num(trade_metrics['ending_equity'],2)}</td></tr>
<tr><th>Total return %</th><td>{fmt_pct(trade_metrics['total_return_pct'])}</td><th>Output directory</th><td>{safe(str(out_dir))}</td></tr>
</table>

<h2>SECTION 2 — SUMMARY METRICS TABLE</h2>
<div class='grid2'><table class='tbl'>
"""

    metric_items = list(trade_metrics["metrics"].items())
    half = (len(metric_items) + 1) // 2
    left = metric_items[:half]
    right = metric_items[half:]
    for k, v in left:
        cls = "val-neg" if isinstance(v, (int, float)) and v < 0 else ""
        val = fmt_num(v, 2) if "(%)" not in k and "Ratio" not in k and "Factor" not in k and "Trades" not in k and "wins" not in k and "losses" not in k else fmt_num(v, 2)
        if "(%)" in k:
            val = fmt_pct(v)
        html_out += f"<tr><th>{safe(k)}</th><td class='{cls}'>{safe(val)}</td></tr>"
    html_out += "</table><table class='tbl'>"
    for k, v in right:
        cls = "val-neg" if isinstance(v, (int, float)) and v < 0 else ""
        val = fmt_pct(v) if "(%)" in k else fmt_num(v, 2)
        html_out += f"<tr><th>{safe(k)}</th><td class='{cls}'>{safe(val)}</td></tr>"
    html_out += "</table></div>"

    html_out += f"""
<h2>SECTION 3 — EQUITY / BALANCE CURVE</h2>
<div class='chart-wrap'><canvas id='eqChart' width='1100' height='280'></canvas></div>
<div class='chart-wrap' style='margin-top:8px;'><canvas id='ddChart' width='1100' height='180'></canvas></div>

<h2>SECTION 4 — MONTHLY / PERIOD RETURNS</h2>
<table class='tbl'><thead><tr><th>Month</th><th>Monthly PnL</th><th>Monthly Return %</th></tr></thead><tbody>
"""
    for m in trade_metrics["monthly"]:
        pnl_cls = "val-neg" if m["pnl"] < 0 else "val-pos"
        html_out += f"<tr><td>{safe(m['month'])}</td><td class='{pnl_cls}'>{fmt_num(m['pnl'],2)}</td><td class='{pnl_cls}'>{fmt_pct(m['return_pct'])}</td></tr>"
    html_out += "</tbody></table>"

    html_out += """
<h2>SECTION 5 — TRADE DISTRIBUTION</h2>
<div class='grid2'>
  <div class='chart-wrap'><div class='small'>PnL Distribution Histogram</div><canvas id='pnlHist' width='520' height='220'></canvas></div>
  <div class='chart-wrap'><div class='small'>Holding Time Distribution (minutes)</div><canvas id='holdHist' width='520' height='220'></canvas></div>
</div>
<div class='grid2' style='margin-top:8px;'>
  <div class='chart-wrap'><div class='small'>PnL by Hour (UTC)</div><canvas id='hourBars' width='520' height='220'></canvas></div>
  <div class='chart-wrap'><div class='small'>PnL by Regime</div><canvas id='regimeBars' width='520' height='220'></canvas></div>
</div>

<h2>SECTION 6 — TOP 5 CANDIDATE COMPARISON</h2>
<table class='tbl'><thead><tr><th>Family ID</th><th>Total Net Profit</th><th>Profit Factor</th><th>Drawdown %</th><th>Total Trades</th><th>Return %</th><th>Win Rate %</th></tr></thead><tbody>
"""
    for t in top5_view:
        html_out += f"<tr><td>{safe(t['family_id'])}</td><td>{fmt_num(t['total_net_profit'],2)}</td><td>{fmt_num(t['profit_factor'],3)}</td><td>{fmt_pct(t['drawdown_pct'])}</td><td>{safe(t['total_trades'])}</td><td>{fmt_pct(t['return_pct'])}</td><td>{fmt_pct(t['win_rate_pct'])}</td></tr>"
    html_out += "</tbody></table>"

    html_out += """
<h2>SECTION 7 — DETAILED TRADE LIST</h2>
<div id='trade-table-wrap'><table class='tbl'><thead><tr>
<th>Trade ID</th><th>Entry Time</th><th>Exit Time</th><th>Side</th><th>Entry Price</th><th>Exit Price</th><th>PnL</th><th>Fees</th><th>Slippage</th><th>Duration (min)</th><th>Setup Type</th>
</tr></thead><tbody>
"""
    for tr in trade_metrics.get("trade_rows", []):
        pnl_cls = "val-neg" if tr["pnl"] < 0 else "val-pos"
        html_out += (
            f"<tr><td>{safe(tr['trade_id'])}</td><td>{safe(tr['entry_time'])}</td><td>{safe(tr['exit_time'])}</td>"
            f"<td>{safe(tr['side'])}</td><td>{fmt_num(tr['entry_price'],2)}</td><td>{fmt_num(tr['exit_price'],2)}</td>"
            f"<td class='{pnl_cls}'>{fmt_num(tr['pnl'],2)}</td><td>{fmt_num(tr['fees'],4)}</td><td>{fmt_num(tr['slippage'],4)}</td>"
            f"<td>{fmt_num(tr['duration'],1)}</td><td>{safe(tr['setup'])}</td></tr>"
        )
    html_out += "</tbody></table></div>"

    verdict = "Promising for paper trading" if trade_metrics["metrics"].get("Profit Factor", 0) > 1.1 and trade_metrics["metrics"].get("Relative Drawdown", 100) < 25 else "Needs more validation"
    risks = "Execution cost drift, regime shift, and outlier dependence."
    html_out += f"""
<h2>SECTION 8 — FINAL VERDICT</h2>
<table class='tbl'>
<tr><th>Research verdict</th><td>{safe(verdict)}</td></tr>
<tr><th>Paper trading recommendation</th><td>{'YES' if 'Promising' in verdict else 'NO / CONDITIONAL'}</td></tr>
<tr><th>Key risks</th><td>{safe(risks)}</td></tr>
</table>

<div class='small' style='margin-top:10px;'>MT4-style adaptation for BTCUSDT research. Self-contained HTML with inline CSS/JS only.</div>
</div>
<script>
const eq = {json.dumps(trade_metrics['equity_points'])};
const dd = {json.dumps(trade_metrics['dd_points'])};
const pnlValues = {json.dumps(trade_metrics['pnl_values'])};
const holdValues = {json.dumps(trade_metrics['holding_mins'])};
const hourMap = {json.dumps(trade_metrics['hourly'])};
const regimeMap = {json.dumps(trade_metrics['regime'])};

function drawLine(canvasId, data, color, yLabel) {{
  const c = document.getElementById(canvasId); if(!c) return;
  const ctx = c.getContext('2d'); const w=c.width,h=c.height,p=36;
  ctx.clearRect(0,0,w,h); ctx.fillStyle='#fff'; ctx.fillRect(0,0,w,h);
  ctx.strokeStyle='#ccc'; ctx.strokeRect(p,10,w-p-8,h-28);
  if(!data.length) return;
  let min=Math.min(...data), max=Math.max(...data); if(min===max){{min-=1;max+=1;}}
  ctx.beginPath(); ctx.strokeStyle=color; ctx.lineWidth=1.5;
  data.forEach((v,i)=>{{
    const x=p + (i*(w-p-10))/Math.max(1,data.length-1);
    const y=10 + (max-v)*(h-40)/(max-min);
    if(i===0) ctx.moveTo(x,y); else ctx.lineTo(x,y);
  }}); ctx.stroke();
  ctx.fillStyle='#444'; ctx.font='11px Tahoma';
  ctx.fillText('0', p-10, h-14); ctx.fillText(String(data.length-1), w-28, h-14);
  ctx.fillText(yLabel+' min: '+min.toFixed(2), p+4, h-14); ctx.fillText('max: '+max.toFixed(2), w-140, h-14);
}}

function histogram(values, bins) {{
  if(!values.length) return {{labels:[],counts:[]}};
  const min=Math.min(...values), max=Math.max(...values);
  const step=(max-min||1)/bins; const counts=Array(bins).fill(0); const labels=[];
  for(let i=0;i<bins;i++) labels.push((min+i*step).toFixed(1));
  values.forEach(v=>{{ let idx=Math.floor((v-min)/step); if(idx>=bins) idx=bins-1; if(idx<0) idx=0; counts[idx]++; }});
  return {{labels,counts}};
}}

function drawBars(canvasId, labels, vals, color) {{
  const c=document.getElementById(canvasId); if(!c) return;
  const ctx=c.getContext('2d'); const w=c.width,h=c.height,p=28;
  ctx.clearRect(0,0,w,h); ctx.strokeStyle='#ccc'; ctx.strokeRect(p,10,w-p-8,h-28);
  if(!vals.length) return; const max=Math.max(...vals.map(v=>Math.abs(v)))||1;
  const barW=(w-p-12)/vals.length;
  vals.forEach((v,i)=>{{
    const x=p+i*barW+1; const hh=Math.abs(v)*(h-48)/max; const y=v>=0?(h-18-hh):(h-18);
    ctx.fillStyle = v>=0 ? color : '#b44'; ctx.fillRect(x,y,Math.max(2,barW-2),hh);
    if(vals.length<=24){{ctx.fillStyle='#555';ctx.font='9px Tahoma';ctx.fillText(String(labels[i]).slice(0,7),x,h-6);}}
  }});
}}

drawLine('eqChart', eq, '#0a62ad', 'Balance');
drawLine('ddChart', dd, '#b00020', 'Drawdown');
const pnlH=histogram(pnlValues, 20); drawBars('pnlHist', pnlH.labels, pnlH.counts, '#0a62ad');
const holdH=histogram(holdValues, 20); drawBars('holdHist', holdH.labels, holdH.counts, '#4b8f29');
const hours=Object.keys(hourMap); drawBars('hourBars', hours, hours.map(k=>hourMap[k]), '#0a62ad');
const regimes=Object.keys(regimeMap).slice(0,10); drawBars('regimeBars', regimes, regimes.map(k=>regimeMap[k]), '#6a4fb3');
</script>
</body></html>
"""

    out_dir.mkdir(parents=True, exist_ok=True)
    out_file.write_text(html_out, encoding="utf-8")
    print(out_file.as_posix())


if __name__ == "__main__":
    main()
