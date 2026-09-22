---
title: Project 1 Roadmap — Entity Resolution and Golden-Record Pipeline
parent_plan: portfolio-project-plan.md
owner: Manish Manoj Nair
created: 2026-09-22
primary_track: Business Analyst (MDM)
secondary_tracks: [Data Engineering, Full-stack (optional Phase 8)]
estimated_effort: 3 weeks core + 1–2 weeks optional UI
learning_mode: agent-assisted (a coding agent implements plumbing; the owner owns every design decision — see Section 10)
agent_context_file: AGENTS.md
status: not started
---

# Project 1 Roadmap: Entity Resolution and Golden-Record Pipeline

## How to use this document

- **Humans:** work through the phases in order. Each phase lists what you'll learn, the tasks, what to hand in, and how to know you're done.
- **Coding agents:** read `AGENTS.md` in the repo root first; its rules override anything here. Work one phase at a time. Implement only tasks marked **Agent** in Section 10; for tasks marked **Owner**, write a stub (signature, docstring, `raise NotImplementedError`) and stop. Do not start a phase until the previous phase's **Acceptance checks** pass.
- Tick checkboxes as tasks finish. Record real numbers in the **Results log** (Section 6), copied only from `reports/metrics.json`. Never fill in a metric that was not measured.

---

## 1. Problem statement

A company holds customer records that were entered by different people, at different times, in different systems. The same person appears several times with typos, missing fields, and inconsistent formatting. The business needs:

1. a measure of how bad the data is,
2. rules that fix what can be fixed,
3. a reliable way to find which records refer to the same person,
4. one trusted **golden record** per person, built by explicit rules, and
5. a queue of uncertain matches for a human data steward to decide.

This is the core loop of Master Data Management (MDM).

## 2. Dataset

**Primary:** Febrl 3 from the Python `recordlinkage` package.

- Load with `recordlinkage.datasets.load_febrl3()`.
- About 5,000 synthetic Australian person records: roughly 2,000 originals plus 3,000 duplicates, with several duplicates per original.
- Fields include: `given_name`, `surname`, `street_number`, `address_1`, `address_2`, `suburb`, `postcode`, `state`, `date_of_birth`, `soc_sec_id`.
- **Ground truth:** the record ID encodes the true entity (e.g. `rec-123-org`, `rec-123-dup-0`). The number in the middle is the true cluster ID.

> Hint: derive a `true_cluster_id` column from the record ID in Phase 1. Every evaluation later depends on it. Confirm the ID format when you first load the data rather than trusting this note.

**Synthetic metadata (needed for survivorship):** Febrl has no source system or timestamp. Survivorship rules are meaningless without them, so add two columns yourself and document that they are synthetic:

- `source_system`: randomly assign CRM, ERP, or WEB_FORM
- `last_updated`: random date within the last 3 years

**Stretch datasets (only after Phase 7):**

- Febrl 4 (`load_febrl4()`): two separate files to *link* rather than dedupe. Tests `link_only` mode.
- Your own Faker-generated data with deliberately injected errors, to check the pipeline isn't overfit to Febrl.

## 3. Stack

| Purpose | Tool |
|---|---|
| Data wrangling | pandas |
| Storage and SQL | DuckDB (single local file, e.g. `data/mdm.duckdb`) |
| Probabilistic matching | Splink (v4; check the docs for your installed version, as the API changed between v3 and v4) |
| Rule definitions | YAML config files |
| Tests | pytest |
| Reports | Markdown + charts (Splink's built-in charts, matplotlib) |
| Optional UI | Spring Boot + React (reuses the Task Tracker stack) |

## 4. Repository structure

```
entity-resolution-mdm/
├── AGENTS.md               # rules for the coding agent (copy to CLAUDE.md if using Claude Code)
├── README.md               # problem, results, how to run
├── RULEBOOK.md             # every DQ, matching, and survivorship rule, in plain English
├── config/
│   ├── dq_rules.yaml       # completeness / validity / standardization rules
│   ├── blocking.yaml       # blocking rules
│   └── survivorship.yaml   # per-field winner rules
├── data/
│   ├── raw/                # untouched source data
│   └── mdm.duckdb          # all intermediate and output tables
├── src/
│   ├── ingest.py           # load Febrl, add ground truth and synthetic metadata
│   ├── profile.py          # data profiling
│   ├── dq_rules.py         # apply rules, flag violations
│   ├── standardize.py      # cleaning / normalization
│   ├── baseline.py         # deterministic matching baseline
│   ├── blocking.py         # blocking analysis
│   ├── model.py            # Splink training and prediction
│   ├── evaluate.py         # pairwise and cluster metrics
│   ├── cluster.py          # thresholds, clustering, review queue
│   ├── survivorship.py     # golden record construction
│   └── scorecard.py        # before/after DQ scorecard
├── reports/                # generated outputs; metrics.json is the single source of numbers
├── tests/                  # unit tests + guard tests (see AGENTS.md)
└── run_pipeline.py         # runs every stage end to end
```

Rule: **every stage reads from DuckDB and writes a new table.** Never overwrite the raw table. This makes each stage inspectable and the whole pipeline reproducible.

---

## 5. Phases

### Phase 0 — Setup (half a day)

- [ ] Create the repo with the structure above and a virtual environment.
- [ ] Add `AGENTS.md` to the repo root (and `CLAUDE.md` as a copy if using Claude Code). Fill in the pinned Splink version once installed.
- [ ] Add the guard tests described in `AGENTS.md` (label-leakage test, raw-table test) before any other code.
- [ ] Pin versions in `requirements.txt` (pandas, duckdb, splink, recordlinkage, pyyaml, pytest).
- [ ] `ingest.py`: load Febrl 3, add `unique_id`, `true_cluster_id`, `source_system`, `last_updated`; write table `raw_customers`.
- [ ] Fix a random seed for the synthetic columns.

**Acceptance checks**
- Running `ingest.py` twice produces identical tables.
- Number of distinct `true_cluster_id` values matches the number of originals you observe.

---

### Phase 1 — Data profiling (2–3 days)

**You'll learn:** how to describe a dataset's quality in numbers before touching it. This is the first thing any MDM or BA engagement asks for.

- [ ] Per column: null / empty-string rate, distinct count, top 10 values, min/max length.
- [ ] Format patterns: map each value to a pattern (e.g. digits → `9`, letters → `A`) and count patterns per column. This exposes format drift quickly.
- [ ] Ground-truth duplicate rate: records ÷ true entities, and the distribution of cluster sizes.
- [ ] Note every problem you see (typos, swapped fields, inconsistent abbreviations) in a list. These become candidate rules in Phase 2.
- [ ] Write `reports/profile.md`.

> Hint: DuckDB SQL is enough for most of this (`COUNT`, `COUNT(DISTINCT ...)`, `regexp_replace` for patterns). Doing it in SQL is good practice for BA interviews.

**Deliverable:** `reports/profile.md` with a table per column and a "problems observed" list.

**Acceptance checks**
- Every column has a completeness figure.
- At least 5 concrete, observed data problems are listed, each with an example value.

---

### Phase 2 — Data-quality rules and standardization (3–4 days)

**You'll learn:** the three standard DQ dimensions used in MDM (completeness, validity, standardization) and how to express rules as config, not hard-coded logic.

- [ ] Write rules in `config/dq_rules.yaml`. Each rule has: `id`, `field`, `dimension`, `description`, `check`, `severity`.
- [ ] **Completeness rules:** which fields are mandatory for a usable customer record? Decide and justify.
- [ ] **Validity rules:** base them on formats you *observed* in Phase 1 (e.g. postcode length, allowed state codes, parseable date of birth). Don't assume formats.
- [ ] **Standardization rules:** trim and case-fold text; expand or unify street abbreviations; normalize dates to one format; strip non-digits from ID-like fields.
- [ ] `dq_rules.py`: evaluate every rule, write a `dq_violations` table (record, rule, value).
- [ ] `standardize.py`: write `std_customers`. Keep original values alongside cleaned ones.
- [ ] Unit tests for each standardization function, including edge cases (empty, null, already clean).
- [ ] Start `RULEBOOK.md` with each rule in plain English.

> Pitfall: over-cleaning. Standardization should never merge distinct values that could be different people (e.g. don't strip middle names that distinguish two people). Only normalize representation.

**Deliverable:** `std_customers` table, `dq_violations` table, rules YAML, tests, rulebook section 1.

**Acceptance checks**
- Rules live in YAML; changing a rule needs no code change.
- Tests pass.
- Violation counts per rule are reported before and after standardization.

---

### Phase 3 — Deterministic baseline and blocking (2–3 days)

**You'll learn:** why exact-match rules fail on real data (this justifies the probabilistic model), and blocking, which is the scaling technique behind every entity-resolution system.

**Part A: baseline**
- [ ] `baseline.py`: declare two records a match if, e.g., standardized surname + date of birth + postcode are equal. Try 2–3 rule variants.
- [ ] Measure pairwise precision, recall, and F1 against ground truth (build the evaluation function in `evaluate.py` now; you'll reuse it).

**Part B: blocking**
- [ ] Compute the number of pairs a full comparison would need: n × (n − 1) / 2.
- [ ] Propose 3–5 blocking rules (e.g. same surname; same date of birth; same postcode + first letter of given name).
- [ ] For each rule and for the union of rules, report: candidate pairs generated, reduction ratio, and **pair completeness** (share of true duplicate pairs that survive blocking).
- [ ] Choose a final set and record the reasoning in `config/blocking.yaml` and the rulebook.

> Hint: Splink ships blocking-analysis helpers (see `splink.blocking_analysis`). Compute pair completeness yourself against ground truth; that's the number that matters and the one interviewers ask about.

> Key trade-off: blocking can only lose true matches, never add them. Pair completeness is the ceiling on your final recall.

**Deliverable:** baseline metrics table; blocking analysis table; chosen blocking rules with justification.

**Acceptance checks**
- Baseline precision/recall are measured, not estimated.
- Chosen blocking keeps pair completeness high (you set and justify the target) while cutting candidate pairs by orders of magnitude.

---

### Phase 4 — Probabilistic matching with Splink (4–5 days)

**You'll learn:** the Fellegi-Sunter model: m-probabilities (how often a field agrees among true matches), u-probabilities (how often it agrees by chance), match weights, and expectation maximization. This is the conceptual core of the project.

- [ ] Read the Splink tutorial and the Fellegi-Sunter explanation in its docs before writing code. Be able to explain m, u, and match weight in your own words.
- [ ] Define comparisons per field, with graded levels (exact, fuzzy by Jaro-Winkler or Levenshtein, else). Pick comparison types to suit each field: names, dates, postcodes, and IDs each need different treatment.
- [ ] Turn on term-frequency adjustments for at least one field (e.g. surname) and understand why: agreeing on a rare surname is stronger evidence than agreeing on a common one.
- [ ] Training sequence (names from Splink v4; verify against your version):
  1. estimate the prior probability that two random records match,
  2. estimate u-probabilities by random sampling,
  3. estimate m-probabilities with EM, using at least two different blocking rules so every field gets trained.
- [ ] Predict pairwise match probabilities over the blocked pairs.
- [ ] Evaluate pairwise precision, recall, F1 against ground truth at several thresholds. Compare with the Phase 3 baseline.
- [ ] Save the trained model settings to JSON so predictions are reproducible.
- [ ] Inspect Splink's match-weights chart and a waterfall chart for a few pairs. Pick one false positive and one false negative and explain *why* the model got each wrong.

> Pitfall: do not use ground-truth labels to train. Train unsupervised with EM, then use labels only to evaluate. Otherwise the result doesn't reflect a real-world setting where labels don't exist.

**Deliverable:** trained model JSON; `reports/model_evaluation.md` with precision/recall vs. threshold, comparison to baseline, and error analysis.

**Acceptance checks**
- You can explain m, u, match weight, and term-frequency adjustment without notes.
- The model beats the deterministic baseline on F1 (if it doesn't, investigate before moving on; that is itself a finding).
- Error analysis covers at least one false positive and one false negative.

---

### Phase 5 — Thresholds, clustering, and the review queue (2 days)

**You'll learn:** how match scores become business decisions, and the transitivity problem in clustering.

- [ ] Choose two thresholds on match probability, giving three bands:
  - **Auto-merge:** above the upper threshold.
  - **Human review:** between the thresholds.
  - **Non-match:** below the lower threshold.
- [ ] Justify the thresholds with the precision/recall curve and with review workload: how many pairs land in the review band? Is that a realistic number for a data steward?
- [ ] Cluster pairwise predictions at the auto-merge threshold (Splink provides connected-components clustering).
- [ ] Evaluate at cluster level: how many true entities were recovered exactly, split into several clusters, or merged with another entity?
- [ ] Write a `review_queue` table: pair, both records side by side, match probability, fields that agree/disagree.

> Concept to understand: transitivity. If A matches B and B matches C, connected components puts A and C together even if A–C scored low. Find one case of this in your output and note whether it was correct.

**Deliverable:** `clusters` table, `review_queue` table, threshold justification in the rulebook.

**Acceptance checks**
- Both thresholds are justified with numbers, not picked arbitrarily.
- Cluster-level metrics are reported alongside pairwise metrics.

---

### Phase 6 — Survivorship and the golden record (3 days)

**You'll learn:** survivorship, which is how MDM systems decide which value "wins" when duplicates disagree. This is the most business-rule-heavy part and the most MDM-specific.

- [ ] For each field, write a rule in `config/survivorship.yaml`. Common rule types:
  - **Source trust:** prefer the most trusted system (define a ranking, e.g. ERP > CRM > WEB_FORM, and justify it).
  - **Most recent:** prefer the value with the latest `last_updated`.
  - **Most complete:** prefer the longest non-null value (useful for addresses).
  - **Most frequent:** majority vote across the cluster.
  - **Validity first:** never let a value that failed a Phase 2 validity rule win if a valid one exists.
- [ ] Define a tie-breaker for every rule.
- [ ] `survivorship.py`: produce `golden_records`, one row per cluster.
- [ ] Record **lineage**: for each golden field, store which source record and which rule supplied it (e.g. a `golden_lineage` table).
- [ ] Unit tests with small hand-built clusters where you know the correct answer, including ties and all-null fields.

> Why lineage matters: in real MDM, stewards and auditors must be able to answer "where did this value come from?" A golden record without lineage would not pass review.

**Deliverable:** `golden_records`, `golden_lineage`, survivorship YAML, tests, rulebook section on survivorship.

**Acceptance checks**
- Every golden field traces back to a source record and a named rule.
- Tests cover ties and all-null clusters.

---

### Phase 7 — Scorecard, documentation, and packaging (2 days)

- [ ] `scorecard.py`: a before/after table covering record count, duplicate rate, completeness per key field, validity rate per rule.
- [ ] `run_pipeline.py`: runs every stage from raw data to scorecard with one command.
- [ ] Finish `RULEBOOK.md`: all DQ, blocking, matching-threshold, and survivorship rules in plain English, with reasoning. Write it for a business stakeholder, not an engineer.
- [ ] `README.md`: problem, approach diagram, headline results (from Section 6), how to run, limitations (including that Febrl and the source/timestamp columns are synthetic).
- [ ] Fresh clone test: clone into a new folder, install, run the pipeline, and confirm the same results.

**Deliverable:** reproducible repo, README, rulebook, scorecard.

**Acceptance checks**
- One command reproduces all results from a fresh clone.
- A non-technical reader can follow the rulebook.

**This is the end of the core project.** Everything below is optional.

---

### Phase 8 (optional) — Stewardship UI (1–2 weeks)

**You'll learn:** turning a data process into a usable workflow; gives full-stack evidence in an MDM context.

- [ ] Spring Boot REST API over the review queue: list pending pairs, get a pair, submit a decision (merge / not a match) with a reviewer name and comment.
- [ ] Decision log table: every decision with timestamp, reviewer, and outcome (an audit trail).
- [ ] React screen: side-by-side comparison with differing fields highlighted, and approve/reject buttons.
- [ ] Feed decisions back: re-run clustering and survivorship so approved merges update the golden records.
- [ ] (Stretch) Use the reviewed decisions as labels to measure how the model performs on the review band specifically.

> Note: moving from DuckDB to a server database (e.g. PostgreSQL) may be simpler for the Spring Boot side. Decide this at the start of the phase, not midway.

**Acceptance checks**
- A decision made in the UI changes the golden record after a pipeline re-run.
- Every decision is logged and retrievable.

### Stretch ideas (only if the core is done)

- Two-source linkage with Febrl 4 (`link_only` mode).
- Run the unchanged pipeline on Faker-generated data to test generalization.
- Incremental matching: add a batch of new records and match them against existing golden records without reprocessing everything.

---

## 6. Results log

Fill in only with measured values.

| Metric | Value | Phase | Notes |
|---|---|---|---|
| Raw record count | | 1 | |
| True entity count | | 1 | |
| Baseline precision / recall / F1 | | 3 | best rule variant |
| Candidate pairs after blocking | | 3 | vs. full comparison |
| Pair completeness after blocking | | 3 | |
| Splink precision / recall / F1 | | 4 | at chosen threshold |
| Pairs in review band | | 5 | |
| Entities recovered exactly | | 5 | cluster-level |
| Golden record count | | 6 | |
| Completeness before → after | | 7 | key fields |

## 7. Timeline

| Week | Phases |
|---|---|
| 1 | 0, 1, 2 |
| 2 | 3, 4 |
| 3 | 5, 6, 7 |
| 4–5 (optional) | 8 |

The timeline is a guide, not a deadline. Phase 4 is where most of the learning is; don't rush it.

## 8. Interview preparation

Be able to answer these once the project is done:

1. Why use probabilistic matching instead of exact-match rules? Show your baseline vs. model numbers.
2. What are m- and u-probabilities, and how does EM estimate them without labels?
3. What does blocking trade off, and how did you choose your rules?
4. Why three decision bands instead of one threshold? How did you size the review band?
5. What is the transitivity problem in clustering, and did you see it?
6. How did you choose survivorship rules, and how do you prove where a golden value came from?
7. What would change in a real company? (Real source systems, real timestamps, steward capacity, incremental loads, governance sign-off.)

## 9. Resume bullet templates

Fill the brackets with measured values from Section 6 only. Delete any bullet whose number you don't have.

- Built an entity-resolution and golden-record pipeline over [N] customer records using Splink (Fellegi-Sunter) and DuckDB, achieving pairwise F1 of [x] vs. [y] for a deterministic rule baseline.
- Designed blocking rules that cut candidate comparisons by [x]% while retaining [y]% of true duplicate pairs.
- Defined [N] data-quality rules and field-level survivorship rules with full value lineage, raising key-field completeness from [x]% to [y]%.
- *(If Phase 8 is done)* Built a Spring Boot + React data-stewardship interface for reviewing uncertain matches, with an audited decision log feeding back into golden records.

---

## 10. Agent workflow

The agent writes plumbing. The owner makes and can defend every decision an interviewer could ask about (Section 8). If a task isn't listed below, default to **Owner decides, Agent implements**.

### 10.1 Ownership by phase

| Phase | Agent implements | Owner does or decides | Owner reviews line by line |
|---|---|---|---|
| 0 Setup | Repo skeleton, `requirements.txt`, `ingest.py`, guard tests | Pin versions; confirm record-ID format | `ingest.py` ground-truth parsing |
| 1 Profiling | Profiling SQL, pattern function, report formatting | The "problems observed" list | — |
| 2 DQ rules | Rule engine that reads YAML, standardization functions, tests | Write every rule in `dq_rules.yaml`; decide mandatory fields | Standardization edge cases |
| 3 Baseline & blocking | Baseline matcher, blocking-count code | Baseline rules; choose blocking rules and justify | — |
| 3 Evaluation | — | **Write `evaluate.py` yourself** | — |
| 4 Splink | Wiring: load data, run training steps, save model JSON, charts | Choose comparisons per field and levels; TF adjustments; EM blocking rules; error analysis | Everything in `model.py` |
| 5 Thresholds | Clustering call, review-queue table | Choose both thresholds; transitivity case | Cluster metric code |
| 6 Survivorship | Engine that applies YAML rules, lineage table, tests | Write every rule in `survivorship.yaml`; source-trust ranking; tie-breakers | Engine logic and tie handling |
| 7 Packaging | `run_pipeline.py`, scorecard formatting, README skeleton | Rulebook prose; README results and limitations | Every number in README |
| 8 UI (optional) | Most of the Spring Boot API and React screen | API design and decision-log schema | Feedback loop into golden records |

### 10.2 Loop for each phase

1. **Brief:** write down the decisions for this phase (rules, thresholds, comparisons) before the agent codes. Put them in the YAML config or in the prompt.
2. **Implement:** give the agent the prompt template below.
3. **Check:** run `pytest` and the phase's acceptance checks yourself. Don't accept "tests pass" from the agent without running them.
4. **Review:** go through the diff using the checklist in 10.4.
5. **Explain:** without notes, explain what this phase's code does and why. If you can't, don't move on.
6. **Commit** with a message naming the phase; tick the checkboxes.

### 10.3 Prompt template

```
Read AGENTS.md and the Phase <N> section of project-1-entity-resolution-roadmap.md.

Implement only the "Agent implements" items for Phase <N> from Section 10.1.
My decisions for this phase: <paste rules / thresholds / comparisons, or "see config/<file>.yaml">.
For "Owner" items, write stubs only.

Done means: <paste the phase's acceptance checks>, and pytest passes including guard tests.
Do not start Phase <N+1>. When finished, list the files you changed and anything you were unsure about.
```

### 10.4 Review checklist

- [ ] No file outside `ingest.py` and `evaluate.py` reads `true_cluster_id` (the guard test should catch this; check anyway).
- [ ] No new dependency that wasn't agreed.
- [ ] No overwriting of `raw_customers` or any earlier stage's table.
- [ ] Rules come from YAML, not hard-coded values.
- [ ] Splink calls match the pinned version's docs.
- [ ] Any number in a report or README exists in `reports/metrics.json`.
- [ ] Nothing from a later phase was added.
