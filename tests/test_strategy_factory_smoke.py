import unittest
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))
from scripts.run_strategy_factory import maybe_make_sample
from src.strategy_factory import run_strategy_factory


class StrategyFactorySmokeTest(unittest.TestCase):
    def test_smoke(self) -> None:
        tmp = Path("outputs") / "_smoke_tmp"
        tmp.mkdir(parents=True, exist_ok=True)
        csv = tmp / "sample.csv"
        out = tmp / "out"
        maybe_make_sample(csv, rows=1200)
        result = run_strategy_factory(csv, n_families=100, output_dir=out)
        self.assertEqual(result["n_generated"], 100)
        self.assertGreater(result["n_evaluated"], 0)
        self.assertTrue((out / "family_catalog.csv").exists())
        self.assertTrue((out / "top5_strategies.json").exists())


if __name__ == "__main__":
    unittest.main()
