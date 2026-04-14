# Reproducibility Failures

1. **Python hash randomization in family parameter seeding** (`src/family_generator.py`).
   - Uses `hash((...))` for RNG seed derivation.
   - Breaks deterministic reproducibility across processes/machines unless hash seed fixed externally.

2. **No explicit global seed contract across entire pipeline**.
   - Some demo data generation seeds (`random.seed(42)`), but core family generation has no user-exposed deterministic seed.

3. **No run manifest / provenance hash**.
   - No durable record of code revision, config, input checksums, and dependency versions.

4. **Shared `outputs/` path with partial cleanup**.
   - Re-runs can consume stale artifacts from earlier runs.

5. **Permissive report readers defaulting to empty/null on parse errors**.
   - Missing/corrupt files may not fail run, causing non-deterministic interpretation behavior.

6. **Environment ambiguity**.
   - No pinned dependency lock; runtime behavior can drift by library/runtime version.

7. **Import-path dependence (`sys.path.append`)**.
   - Execution behavior tied to filesystem context rather than package install discipline.
