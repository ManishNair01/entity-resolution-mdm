# Phase 1 changes

Everything changed on branch `phase-1-profiling` relative to `main`, none of it
committed yet. Written 2026-09-24, updated 2026-09-27.

---

## Files

| File | Status | What changed |
|---|---|---|
| `src/profile.py` | New | Profiling stage: DuckDB profiling SQL, the pattern function, and the `reports/profile.md` formatting |
| `reports/profile.md` | New, generated | The profile report. "Problems observed" is `[TBD]` for the owner |
| `src/ingest.py` | Modified | Writes one extra metric, `ingest.cluster_size_distribution` |
| `run_pipeline.py` | Modified | Adds `profile` as the next stage after `ingest` in `STAGES` |
| `OPEN-DECISIONS.md` | Modified | Adds Open items 6 and 7; rewrites "Needed before the next phase" for Phase 1 |

---

## Details

### `src/profile.py` (new)

Run with `python -m src.profile`, or as part of `python run_pipeline.py`.

- **Columns profiled:** the 10 Febrl fields plus the synthetic `source_system`
  and `last_updated`. `unique_id` is excluded because it's a surrogate key with no
  data-quality story, and the ground-truth columns are excluded because of hard rule 1.
- **Per column:** row count, null count and rate, empty-string count and rate,
  distinct count, min and max length, top 10 values, number of distinct format
  patterns, and the top 10 patterns.
- **Pattern function (`pattern_expr`):** replaces each digit with `9` and each
  ASCII letter with `A`, and leaves everything else as it is, e.g.
  `"2/48"` → `"9/99"`.
- **Duplicate rate and cluster sizes:** read back from the `ingest.*` metrics in
  `reports/metrics.json`. The module never touches the ground-truth columns
  directly.
- **Database access:** opens `data/mdm.duckdb` read-only.
- **Metrics:** every per-column number is written to `reports/metrics.json` as
  `profile.<column>.<stat>`, and the duplication numbers as
  `profile.duplicate_rate`, `profile.cluster_size_min` and
  `profile.cluster_size_max`.
- **Report built from `metrics.json` only.** `run()` writes the metrics, reads
  `reports/metrics.json` back, and builds the whole report from what it loaded
  (`unflatten_profile()` → `format_report()`). This was changed this session:
  the column tables used to be built from values still in memory. The
  regenerated report was byte-identical before and after the change.

### `src/ingest.py`

- New metric `ingest.cluster_size_distribution`: cluster size → number of
  clusters of that size.
- It's computed in `ingest.py` because hard rule 1 only lets `ingest.py` and
  `evaluate.py` group by the ground-truth entity. Logged as Open item 6.
- `raw_customers` and the existing metrics are unchanged.

### `run_pipeline.py`

- `STAGES` is now `ingest` → `profile`, and the docstring was updated to match.

### `OPEN-DECISIONS.md`

- **Item 6 (Open):** the cluster-size distribution needed a change to `ingest.py`, not just `profile.py`.
- **Item 7 (Open):** the definition of "duplicate rate". Added this session.
- "Needed before the next phase" now says the Phase 1 agent work is done and the
  "problems observed" list is the owner's to write.

---

## Verification

| Check | Result |
|---|---|
| `pytest` (including both guard tests) | 7 passed |
| Two runs give identical output | `reports/profile.md` has the same SHA-256 hash across reruns |
| Report rebuilt from `metrics.json` | Output identical to the previous in-memory version |
| Leakage | `src/profile.py` never mentions `true_cluster_id` or `rec_id` |
| Phase 2 not started | No Phase 2 files added |

---

## Update 2026-09-27

Items 6 and 7 were decided on 2026-09-26 (see `OPEN-DECISIONS.md`), and the
owner wrote the problems list (P1–P8) in `reports/problems_observed.md`. Fixes
made this session:

| File | Change |
|---|---|
| `src/profile.py` | **Duplicate rate** now follows the 2026-09-26 decision: duplicate records ÷ records (60.00%). Records per entity (2.500) is reported separately as `profile.records_per_entity`. |
| `src/profile.py` | **Problems list embedded, never overwritten.** Reads `reports/problems_observed.md` and copies it verbatim into the "Problems observed" section; `[TBD]` if the file is missing. Before this, regenerating `profile.md` erased anything written in it. |
| `src/profile.py` | `load_existing_metrics()` looks up `ingest.METRICS_PATH` at call time instead of an import-time copy, so reads and writes always hit the same file. |
| `src/profile.py` | Docstring fixes: `unique_id` is hash-ordered, not sequential; `"O'Brien"` → `"A'AAAAA"`. |
| `tests/test_raw_untouched.py` | **Test isolation bug fixed.** The fixture redirected ingest's outputs but not the profile report, so every `pytest` run overwrote the real `reports/profile.md`. It now also redirects `profile.REPORT_PATH` and `profile.PROBLEMS_PATH`, and a new test fails if a test run touches `reports/profile.md`. |
| `tests/test_profile_report.py` | New: duplicate-rate definitions, problems-section embedding / `[TBD]` fallback, and `run()` never writing the problems file. |
| `README.md`, `OPEN-DECISIONS.md` | Status line; decision on where the problems list lives. |

Verification: `pytest` 13 passed; two pipeline runs give an identical
`reports/profile.md` (SHA-256 `e42a4bac…`); the embedded problems section is
identical to `problems_observed.md` apart from the final newline; `reports/profile.md`
is unchanged by a `pytest` run.

## Waiting on the owner

1. **Review the diff**, then commit and open the Phase 1 PR. `src/profile.py`,
   `reports/profile.md`, `reports/problems_observed.md`,
   `tests/test_profile_report.py` and `PHASE-1-CHANGES.md` are untracked, so
   `git add` them first.
2. **`notes/`:** commit your investigation scripts as evidence, or add the folder
   to `.gitignore`. They query ground truth directly, which is fine outside `src/`.
