# CONSISTENCY_FINDINGS

## Scope
Compared ranking source tables, top-5 markdown/json artifacts, deep-dive comparison memo, and HTML report logic.

## Findings

1. **Top-5 ranking consistency (current outputs) — PASS**
   - Recomputed ranking from `family_backtest_results.csv` + `family_robustness_results.csv` reproduces `top5_strategies.json` ordering exactly.

2. **HTML consistency guards — PASS**
   - `scripts/build_html_report.py` includes assertions to enforce top-5 card IDs and robust scores match leaderboard source.

3. **Cross-artifact narrative consistency (top5 vs deep-dive) — WARNING**
   - `fam_comparison.md` promotes FAM_0039 over FAM_0053 from a separate workflow context, while top-5 artifacts are FAM_0108/FAM_0084/etc.
   - Without explicit run IDs and provenance tags, investor readers may interpret these as one unified ranking context.

4. **Score semantics clarity — WARNING**
   - Robustness score is normalized relative to run cohort; it is not an absolute metric. Report language should consistently emphasize this to avoid cross-run misuse.

## Suggested controls
- Stamp every artifact with `run_id`, data hash, timestamp range, and ranking parameters.
- Disallow mixed-run report assembly unless explicitly intended and labeled.
- Add a machine-readable manifest tying every report component to exact source files.
