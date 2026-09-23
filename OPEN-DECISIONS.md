# Open decisions

Things the agent needs from the owner, and the decisions already made. The agent
adds to this file whenever it hits a choice that belongs to the owner
(`AGENTS.md`, "Owner-owned decisions"), or makes an assumption to keep moving.

**Owner:** Manish Manoj Nair · **Last updated:** 2026-09-22 (end of Phase 0)

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

### 3. Should the leakage guard also cover `rec_id`?

`rec_id` encodes the entity just as plainly as `true_cluster_id`, and it sits in
`raw_customers`. Passing it to Splink would leak labels, but
`tests/test_no_label_leakage.py` only looks for the `true_cluster_id` string,
which is what `AGENTS.md` specifies.

*Assumed:* the test stays as specified. Say the word and the agent extends it to
`rec_id`, with `ingest.py` and `evaluate.py` still exempt.

### 4. Where do the ingest constants belong?

`RANDOM_SEED = 42`, `LAST_UPDATED_REFERENCE_DATE = 2026-09-22`, and a 3-year
window are constants at the top of `src/ingest.py`. They are not DQ, blocking or
survivorship rules, so the config rule does not clearly cover them.

*Assumed:* they stay in `ingest.py`. They can move to a config file if you would
rather every tunable value live in YAML.

### 5. Is the raw CSV snapshot worth tracking in git?

`data/raw/febrl3.csv` is committed (469 KB, 5,000 rows). It matches the roadmap's
`data/raw/` structure and makes the input inspectable on GitHub, but it is
regenerable from `recordlinkage` at any time.

*Assumed:* keep it tracked.

### 6. Per-phase pull requests, or commit straight to `main`?

Phase 0's reproducibility work went through PR #1. For a solo repo that is
optional ceremony — though it does give a diff to review against the §10.4
checklist, which is a step in your own workflow.

*Assumed:* keep opening a PR per phase until told otherwise.

---

## Needed before the next phase

**Phase 1 — profiling.** The agent writes the profiling SQL, the pattern
function and the report formatting. The **"problems observed" list is yours**
(§10.1): at least five concrete problems, each with a real example value. It
feeds directly into the Phase 2 rules, and it is the part an interviewer will
ask you to defend. Suggested order: the agent generates the profile tables
first, you read them and write the list from what you actually see.

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
