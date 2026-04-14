from __future__ import annotations

import csv
import subprocess
import sys
from pathlib import Path


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def test_report_discloses_capital_model_and_trade_notional(tmp_path: Path) -> None:
    out_dir = tmp_path / "outputs"
    report_path = out_dir / "strategy_factory_report.html"
    script_path = Path(__file__).resolve().parents[1] / "scripts" / "build_html_report.py"

    _write_csv(
        out_dir / "family_backtest_results.csv",
        [
            {
                "family_id": "FAM_0001",
                "family_name": "Family 1",
                "hypothesis_class": "trend",
                "train_net_pnl": 100,
                "validation_net_pnl": 90,
                "oos_net_pnl": 80,
                "starting_capital": 10000,
                "ending_equity": 10080,
                "oos_return_pct": 0.8,
                "train_profit_factor": 1.2,
                "validation_profit_factor": 1.1,
                "oos_profit_factor": 1.05,
                "train_expectancy": 10,
                "validation_expectancy": 9,
                "oos_expectancy": 8,
                "max_drawdown": -100,
                "max_drawdown_pct": -1.0,
                "trade_count": 25,
                "risk_per_trade_pct": 0.2,
                "max_leverage": 2.0,
            }
        ],
    )
    _write_csv(
        out_dir / "family_robustness_results.csv",
        [
            {
                "family_id": "FAM_0001",
                "fee_stress_pnl_delta": -5,
                "slippage_stress_pnl_delta": -4,
                "parameter_stability": 0.7,
                "outlier_dependence": 0.2,
                "baseline_oos_trade_count": 25,
            }
        ],
    )
    _write_csv(
        out_dir / "top5_trade_journals" / "FAM_0001.csv",
        [
            {
                "timestamp_entry": "2026-01-01T00:00:00+00:00",
                "timestamp_exit": "2026-01-01T00:05:00+00:00",
                "entry_time": "2026-01-01T00:00:00+00:00",
                "exit_time": "2026-01-01T00:05:00+00:00",
                "side": "long",
                "quantity": 1.5,
                "entry_notional": 150.0,
                "net_pnl": 10.0,
                "gross_pnl": 12.0,
                "fees": 1.0,
                "slippage_cost": 0.5,
                "leverage_used_or_gross_exposure": 0.02,
            }
        ],
    )

    subprocess.run([sys.executable, str(script_path), "--output-dir", str(out_dir), "--out-file", str(report_path)], check=True)
    html = report_path.read_text(encoding="utf-8")

    assert "Initial capital (USD)" in html
    assert "10,000.00" in html
    assert "Sizing model" in html
    assert "equity-based" in html
    assert "Peak leverage used" in html
    assert "entry_notional" in html
    assert ">qty<" in html
