# STANFORD Reproducibility Log

## Environment
- Date: 2026-04-12 (UTC)
- Repo: `/workspace/100scalppm`
- Dataset: `data/samples/btcusdt_1m_large.csv` (50,000 rows)

## Commands Run
1. `python scripts/run_strategy_factory.py --csv data/samples/btcusdt_1m_large.csv --n-families 120 --min-trades 20 --output-dir outputs --initial-capital 10000`
   - Success.
2. `python scripts/run_deep_dive_candidates.py --csv data/samples/btcusdt_1m_large.csv --output-dir outputs --n-families 120 --min-trades 20 --min-trades-alt 30 --initial-capital 10000`
   - Success.
3. `python scripts/build_html_report.py --output-dir outputs --initial-capital 10000`
   - Failed (`ValueError` on `Path(tf).relative_to(ROOT)` due to relative path handling).
4. `python scripts/build_mt4_html_report.py --output-dir outputs --initial-capital 10000`
   - Success.
5. Multiple ad-hoc Python recomputation checks from top-5 trade journals.
6. Determinism checks across subprocess invocations of `generate_strategy_families(120)`.

## Reproduction Result
- Core pipeline runs, but full report pipeline not clean due to path bug.
- Strategy identity is not deterministic across processes.
- Therefore outputs are **not cleanly reproducible** in institutional sense.
