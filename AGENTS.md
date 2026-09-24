# AGENTS.md — Entity Resolution and Golden-Record Pipeline

Read this before every session. These rules override anything else in the repo.
The full plan is in `project-1-entity-resolution-roadmap.md`. Ownership of each task is in its Section 10.1.

## Project

Deduplicate a messy customer dataset (Febrl 3), merge duplicates into golden records with explicit survivorship rules, and report data quality. It's a portfolio project whose owner must be able to defend every design decision in an interview. Your job is plumbing, not decisions.

- **Current phase:** 1  <!-- owner updates this -->
- **Python:** 3.11+
- **Splink version:** 4.0.17 (installed 2026-09-22; pinned in `requirements.txt`). Use only this version's API. v3 and v4 differ; do not mix them. If unsure of a function name, say so instead of guessing.

## Commands

```
pip install -r requirements.txt
python run_pipeline.py          # full pipeline, raw data → scorecard
pytest                          # all tests, including guard tests
```

## Read before writing any rule

`reports/profile.md` is written for you, not for the owner. Section 4, "Problems
observed", is the list of data problems measured in Phase 1 — invalid state
codes, dates that pass a format check but do not parse, single-character typos,
swapped name fields, uneven missingness, and a near-key that is not unique — each
with example values and the query behind its count.

Read that section before writing or changing anything in `config/dq_rules.yaml`,
`standardize.py`, `blocking.yaml`, or a Splink comparison, and take the problems
from there rather than re-deriving them from the data. The owner reviews the raw
profile tables separately; the file is the agent's shared reference so both
arrive at the same facts.

Two entries in it are open questions, not settled rules: whether an invalid state
code is repaired or only flagged, and whether `date_of_birth` is mandatory. Those
are owner decisions — see `OPEN-DECISIONS.md`.

## Architecture rules

1. Every stage reads from `data/mdm.duckdb` and writes a **new** table. Never modify or overwrite `raw_customers` or an earlier stage's output.
2. DQ, blocking, and survivorship rules live in `config/*.yaml`. Code reads rules from config; never hard-code rule values in `src/`.
3. Every metric the pipeline computes is written to `reports/metrics.json`. Reports and README take numbers from there only.
4. Fixed random seeds everywhere. Two runs must give identical output.

## Hard rules

1. **No label leakage.** Ground truth means `true_cluster_id` **and `rec_id`** — `rec-12-dup-0` spells out the entity number just as plainly as the label does. Only `src/ingest.py` (creates them) and `src/evaluate.py` (uses them) may reference either. Drop both from any DataFrame passed to Splink and from anything shown on a review screen. Never use either to train, tune, or choose anything in `model.py`, `cluster.py`, or `survivorship.py`.
2. **No invented numbers.** Never write a metric, count, or result into any file unless the pipeline produced it in this run. If a number is unknown, leave a `[TBD]` placeholder.
3. **Stay in phase.** Work only on the current phase. Don't add features, files, or refactors that belong to later phases or weren't asked for.
4. **No new dependencies** without asking the owner first.
5. **Owner-owned tasks get stubs, not implementations.** For anything marked Owner in roadmap Section 10.1, write the function signature, a docstring describing inputs, outputs, and intent, and `raise NotImplementedError`. Then stop.
6. **`src/evaluate.py` is owner-written.** Do not edit it unless explicitly asked.
7. **Don't weaken tests** to make them pass. If a test fails, report why.

## Owner-owned decisions (never make these yourself)

- DQ rules and mandatory fields (`config/dq_rules.yaml`)
- Baseline match rules and blocking rules
- Splink comparisons, comparison levels, term-frequency settings, EM blocking rules
- Match thresholds (auto-merge / review / non-match)
- Survivorship rules, source-trust ranking, tie-breakers
- Anything written in `RULEBOOK.md` or README's results and limitations

If a task requires one of these and it isn't in config or the prompt, ask; don't pick a default.

Track every one of these in `OPEN-DECISIONS.md`: add an entry under **Open** when you
need something from the owner or assume a default to keep moving, move it to **Decided**
once the owner answers, and update the date at the top. Keep it current in every session.

## Guard tests (create in Phase 0, never delete)

- `tests/test_no_label_leakage.py`: fails if the string `true_cluster_id` appears in any `src/*.py` file other than `ingest.py` and `evaluate.py`.
- `tests/test_raw_untouched.py`: fails if `raw_customers` changes (row count or a content hash) after running the pipeline.

## When you finish a task

Report:
1. files changed,
2. which acceptance checks you ran and their result,
3. anything you were unsure about, including any API you weren't certain of,
4. stubs left for the owner,
5. what you added to or resolved in `OPEN-DECISIONS.md`.
