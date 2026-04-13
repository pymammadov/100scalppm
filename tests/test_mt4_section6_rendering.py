from __future__ import annotations

import csv
import re
import subprocess
import sys
from pathlib import Path


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _extract_section6_rows(html: str) -> list[str]:
    section6 = re.search(
        r"SECTION 6 — TOP 5 CANDIDATE COMPARISON</h2>\s*<table class='tbl'>.*?<tbody>(.*?)</tbody>",
        html,
        flags=re.DOTALL,
    )
    assert section6 is not None, "SECTION 6 table not found in generated report"
    return re.findall(r"<tr>(.*?)</tr>", section6.group(1), flags=re.DOTALL)


def test_section6_renders_exactly_one_unique_row_per_top5_candidate(tmp_path: Path) -> None:
    out_dir = tmp_path / "outputs" / "spot_15m"
    script_path = Path(__file__).resolve().parents[1] / "scripts" / "build_mt4_html_report.py"
    report_path = out_dir / "mt4_style_report.html"

    backtest_rows = []
    robust_rows = []
    for i in range(1, 6):
        fam = f"FAM_{i:04d}"
        backtest_rows.append(
            {
                "family_id": fam,
                "family_name": f"Family {i}",
                "oos_net_pnl": 1000 - i * 10,
                "oos_profit_factor": 1.2 + i / 100.0,
                "max_drawdown": 150 + i,
                "max_drawdown_pct": 10 + i / 10.0,
                "trade_count": 30 + i,
                "oos_return_pct": 5 + i / 10.0,
                "train_net_pnl": 1100 - i * 10,
                "validation_net_pnl": 950 - i * 10,
                "oos_expectancy": 20 + i,
            }
        )
        robust_rows.append(
            {
                "family_id": fam,
                "fee_stress_pnl_delta": -10 - i,
                "slippage_stress_pnl_delta": -12 - i,
                "parameter_stability": 0.8,
                "outlier_dependence": 0.2,
            }
        )
        _write_csv(
            out_dir / "top5_trade_journals" / f"{fam}.csv",
            [
                {
                    "trade_id": j,
                    "timestamp_entry": f"2025-01-{j:02d} 00:00:00",
                    "timestamp_exit": f"2025-01-{j:02d} 01:00:00",
                    "net_pnl": 50 if j % 2 == 0 else -20,
                    "timeframe": "15m",
                }
                for j in range(1, 7)
            ],
        )

    _write_csv(out_dir / "family_backtest_results.csv", backtest_rows)
    _write_csv(out_dir / "family_robustness_results.csv", robust_rows)

    subprocess.run(
        [sys.executable, str(script_path), "--output-dir", str(out_dir), "--out-file", str(report_path)],
        check=True,
    )

    html = report_path.read_text(encoding="utf-8")
    row_html = _extract_section6_rows(html)
    assert len(row_html) == 5

    family_ids = []
    for row in row_html:
        cells = re.findall(r"<td>(.*?)</td>", row)
        assert len(cells) == 7
        family_ids.append(re.sub(r"<.*?>", "", cells[0]))

    assert len(set(family_ids)) == 5
