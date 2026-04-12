# REPRODUCIBILITY_LOG

Date: 2026-04-12 UTC
Branch: `investor-audit`

## Repository setup
1. `git checkout -b investor-audit`
   - Result: success.

## Survey commands
2. `rg --files`
   - Result: success, enumerated source/scripts/outputs/tests.
3. `sed -n '1,220p' src/ranking.py` (and analogous file inspections)
   - Result: success, reviewed ranking/evaluation/reporting logic.

## Reproducibility and test commands
4. `python -m unittest -v`
   - Result: success technically, but discovered **0 tests**.
5. `python -m unittest -v tests/test_strategy_factory_smoke.py`
   - Result: success, 2 tests passed.

## Workflow runs
6. `python scripts/run_strategy_factory.py --csv data/samples/btcusdt_1m_sample.csv --n-families 120 --min-trades 20 --output-dir outputs/_audit_run`
   - Result: success (`Generated 120 families`, `Evaluated 120 families`).
7. `python scripts/run_deep_dive_candidates.py --csv data/samples/btcusdt_1m_sample.csv --output-dir outputs/_audit_run --n-families 120 --min-trades 20 --min-trades-alt 30`
   - Result: success (`Deep dive complete. Stronger candidate: FAM_0039`).
8. `python scripts/build_html_report.py`
   - Result: success (`outputs/strategy_factory_report.html` generated).

## Consistency and metric checks
9. Python check: recomputed ranking from `family_backtest_results.csv` + `family_robustness_results.csv` and compared with `top5_strategies.json`
   - Result: success, exact top-5 match.
10. Python check: top5 journal cost breakdown and holding times
   - Result: success; showed substantial gross-to-net erosion by fees/slippage.
11. Python check: top5 parameter similarity from `family_catalog.csv`
   - Result: success; top candidates are closely related variants.

## Environment blockers
- No package installation required for current runs.
- No external market data ingestion executed in this audit context.
