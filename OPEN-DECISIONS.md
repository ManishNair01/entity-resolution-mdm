# Open decisions

Things the agent needs from the owner, and the decisions already made. The agent
adds to this file whenever it hits a choice that belongs to the owner
(`AGENTS.md`, "Owner-owned decisions"), or makes an assumption to keep moving.

**Owner:** Manish Manoj Nair · **Last updated:** 2026-09-24 (Phase 1 profiling)

- **Open** — waiting on you. The agent has assumed something in the meantime;
  each entry says what.
- **Decided** — settled. Kept so the reasoning survives, because interview
  questions come from this list.

---

## Open

### 1. Record-ID format (Phase 0, §10.1 line-by-line review item)

Ground truth is parsed as `rec-<N>-org` and `rec-<N>-dup-<k>`, with `<N>` as the
entity. Observed in the installed data: 2,000 `-org` and 3,000 `-dup-` rows over
2,000 distinct `<N>`.

*Assumed:* that reading, in `src/ingest.py`. Anything not matching the pattern
raises rather than producing wrong labels. **Every later metric depends on this
being right.**

### 2. Dependency pins

Pinned to whatever installed on 2026-09-22: `pandas==2.3.3`, `duckdb==1.5.5`,
`splink==4.0.17`, `recordlinkage==0.16`, `PyYAML==6.0.3`, `pytest==9.1.1`.
Splink 4 means the **v4 API**; v3 examples found online will not work.

*Assumed:* these pins are acceptable.

### 3. Where do the ingest constants belong?

`RANDOM_SEED = 42`, `LAST_UPDATED_REFERENCE_DATE = 2026-09-22`, and a 3-year
window are constants at the top of `src/ingest.py`. They are not DQ, blocking or
survivorship rules, so the config rule does not clearly cover them.

*Assumed:* they stay in `ingest.py`. They can move to a config file if you would
rather every tunable value live in YAML.

### 4. Is the raw CSV snapshot worth tracking in git?

`data/raw/febrl3.csv` is committed (469 KB, 5,000 rows). It matches the roadmap's
`data/raw/` structure and makes the input inspectable on GitHub, but it is
regenerable from `recordlinkage` at any time.

*Assumed:* keep it tracked.

### 5. Per-phase pull requests, or commit straight to `main`?

Phase 0's reproducibility work went through PR #1. For a solo repo that is
optional ceremony — though it does give a diff to review against the §10.4
checklist, which is a step in your own workflow.

*Assumed:* keep opening a PR per phase until told otherwise.

### 6. How Phase 1 reports duplication without reading the label

The duplicate rate and cluster-size distribution are ground-truth figures, but
hard rule 1 keeps `true_cluster_id` inside `ingest.py`. So `ingest.py` now also
writes `ground_truth_cluster_sizes`: one row per cluster size, holding how many
entities have that many records. `profile.py` reads that aggregate, which cannot
be traced back to any record.

*Assumed:* an aggregate with no per-record label is not leakage, and extending
`ingest.py` for it is better than letting a second module see the label. The
alternative — profiling duplication inside `ingest.py` — would put a Phase 1
deliverable in the Phase 0 module.

### 7. Format patterns do not distinguish case

The roadmap says letters map to `A`, so `nsw` and `NSW` share the pattern `AAA`
and case drift is invisible in the profile. Mapping upper-case to `A` and
lower-case to `a` would expose it.

*Assumed:* the roadmap's spec, as written. Febrl 3 is lower-case throughout, and
Phase 2 case-folds anyway, so nothing is lost here — but say the word and the
pattern function will split the two.

### 8. The report shows two pattern views

The literal pattern encodes length, so a name column's top ten patterns are ten
different lengths and the handful of values carrying a hyphen or a space never
surface. The report therefore also shows a "shape": the same pattern with runs of
one symbol collapsed, so `1942-08-04` becomes `9-9-9` and `mary-jane` becomes
`A-A`.

*Assumed:* both views earn their space. Drop the shape tables if the report reads
as too long.

### 9. Which numbers go into `metrics.json`

Architecture rule 3 says reports take numbers from `metrics.json` only. Every
headline figure does: per-column completeness, nulls, blanks, distinct counts,
lengths, pattern and shape counts, and the duplication figures. The top-values and
top-patterns tables do not — they are roughly 220 rows of per-value detail, and
they come from the `profile_*` DuckDB tables written in the same run.

*Assumed:* "metric" means the headline numbers, not every cell of every detail
table.

### 10. The "problems observed" list is a placeholder, not a `NotImplementedError`

Rule 5 asks for owner-owned work to raise. A raise here would break
`run_pipeline.py`, so `profile.py` instead writes a `[TBD]` block into section 4
of `reports/profile.md`. Anything you write between the `problems-observed`
markers is preserved when the report is regenerated; the rest of the file is
overwritten every run.

*Assumed:* a visible `[TBD]` beats a pipeline that cannot run to the end.

---

## Needed before the next phase

**Phase 1 — profiling.** The profile tables and `reports/profile.md` are
generated. What is left is yours and it is the acceptance check that still fails:
the **"problems observed" list** (§10.1), at least five concrete problems, each
with a real example value. Write it into section 4 of `reports/profile.md`,
between the `problems-observed` markers, where re-runs will not overwrite it. It
feeds directly into the Phase 2 rules, and it is the part an interviewer will ask
you to defend — so write it from what the tables actually show.

**Phase 2 — DQ rules.** Nothing can start until the list above exists, since the
validity rules are supposed to come from observed formats rather than assumed
ones.

---

## Decided

| Date | Decision | Notes |
|---|---|---|
| 2026-09-22 | Python 3.11 via `py -3.11`; venv at `.venv` | The machine's default `python` is 3.9 |
| 2026-09-22 | Repo `entity-resolution-mdm`, public, MIT | Description and topics set in the GitHub UI |
| 2026-09-22 | Derive synthetic values by hash, not RNG | Makes the fresh-clone test reproducible across platforms, Python versions and input order |
| 2026-09-22 | `unique_id` = rank of a hash of `rec_id` | Sequential IDs in `rec_id` order would have leaked the entity through the key itself |
| 2026-09-22 | Commit the reports, ignore `reports/metrics.json` only | `profile.md` and the scorecard are deliverables; the metrics file churns every run |
| 2026-09-22 | Synthetic `source_system` and `last_updated` | Roadmap §2. Uniform over CRM / ERP / WEB_FORM and over the 3 years to 2026-09-22; documented as synthetic in the README |
| 2026-09-23 | No second issue tracker: reverted the GitHub-issues / triage-label / ADR skill setup | `AGENTS.md` and `OPEN-DECISIONS.md` already carry the decisions for a solo, single-repo project; the setup duplicated that ledger and was out of phase. Don't re-run it. |
| 2026-09-23 | The leakage guard covers `rec_id` as well as `true_cluster_id` | `rec-12-dup-0` names the entity as plainly as the label does, so leaving it unguarded would let the matching code cheat instead of matching. `AGENTS.md` rule 1 and `tests/test_no_label_leakage.py` now cover both strings; `ingest.py` and `evaluate.py` stay exempt |

---

## Assumptions recorded in code

Each is a decision the agent made to keep moving. Overrule any of them.

- Source systems are drawn uniformly, so the three systems hold roughly a third
  of the records each. Real systems are rarely balanced; if you want the
  survivorship story in Phase 6 to be more realistic, an uneven split would
  reflect that better.
- `last_updated` is uniform over the 3 years to `LAST_UPDATED_REFERENCE_DATE`,
  with no correlation to `source_system` or to whether a record is an original
  or a duplicate.
- `reports/metrics.json` keys are namespaced by stage, e.g. `ingest.record_count`.
