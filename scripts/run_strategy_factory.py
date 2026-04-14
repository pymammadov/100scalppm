from __future__ import annotations

import argparse
import sys
import csv
import math
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))
from scripts.output_contract import ensure_artifacts_in_output_dir
from src.strategy_factory import run_strategy_factory


def maybe_make_sample(csv_path: Path, rows: int = 6000) -> None:
    if csv_path.exists():
        return
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    random.seed(42)
    start = datetime(2025, 1, 1, tzinfo=timezone.utc)
    price = 42000.0
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["timestamp", "open", "high", "low", "close", "volume"])
        w.writeheader()
        for i in range(rows):
            ts = start + timedelta(minutes=i)
            shock = random.gauss(0, 0.0008) + 0.0002 * math.sin(i / 60)
            next_price = price * (1 + shock)
            spread = max(3.0, next_price * random.uniform(0.0001, 0.0010))
            high = max(price, next_price) + spread * random.uniform(0.2, 1.2)
            low = min(price, next_price) - spread * random.uniform(0.2, 1.2)
            volume = math.exp(random.gauss(8, 0.45))
            w.writerow(
                {
                    "timestamp": ts.isoformat().replace("+00:00", "Z"),
                    "open": f"{price:.6f}",
                    "high": f"{high:.6f}",
                    "low": f"{low:.6f}",
                    "close": f"{next_price:.6f}",
                    "volume": f"{volume:.6f}",
                }
            )
            price = next_price


def main() -> None:
    parser = argparse.ArgumentParser(description="Run open strategy factory discovery pipeline")
    parser.add_argument("--csv", type=Path, required=True, help="Path to BTCUSDT 1m OHLCV CSV")
    parser.add_argument("--n-families", type=int, default=120)
    parser.add_argument("--min-trades", type=int, default=20)
    parser.add_argument("--output-dir", type=Path, default=Path("outputs"))
    parser.add_argument("--initial-capital", type=float, default=10000.0)
    parser.add_argument("--build-sample-if-missing", action="store_true")
    args = parser.parse_args()

    if args.build_sample_if_missing:
        maybe_make_sample(args.csv)

    result = run_strategy_factory(
        args.csv,
        args.n_families,
        args.output_dir,
        min_trades=args.min_trades,
        initial_capital=args.initial_capital,
    )
    moved = ensure_artifacts_in_output_dir(
        args.output_dir,
        [
            "top5_strategies.json",
            "top5_strategies.md",
            "strategy_factory_summary.json",
            "strategy_factory_summary.md",
            "family_backtest_results.csv",
            "family_robustness_results.csv",
            "family_catalog.csv",
            "failure_taxonomy.json",
            "regime_survival_table.csv",
        ],
    )
    if moved:
        print("Relocated legacy artifacts into --output-dir:", [str(p) for p in moved])
    print(f"Generated {result['n_generated']} families")
    print(f"Evaluated {result['n_evaluated']} families")
    print("Top 5 family_ids:", [x["family_id"] for x in result["top5"]])


if __name__ == "__main__":
    main()
