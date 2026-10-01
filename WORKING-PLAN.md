# Working plan — entity resolution and golden records

Updated: 2026-09-29

This is the execution companion to `project-1-entity-resolution-roadmap.md`,
especially its ownership table in Section 10.1. `AGENTS.md` remains authoritative.
The owner requested planning for every phase; implementation remains limited to
Phase 2 until the owner advances the current phase. Future checkboxes are planned
work, not authorization to implement it now.

## Starting point

| Phase | Repository evidence | Next action |
|---|---|---|
| 0 — Setup | Ingest, pinned requirements and guard tests exist | Retain and recheck the acceptance evidence |
| 1 — Profiling | Profiling code, report and observed-problems file exist | Retain and confirm owner review |
| 2 — DQ and standardization | Config, engines, age review and tests exist; current phase | Close open assumptions and verify acceptance |
| 3–7 — Remaining core | Not wired into `run_pipeline.py` | Execute sequentially after phase gates |
| 8 — Stewardship UI | Optional roadmap scope | Decide whether to pursue after core completion |

Presence of files does not prove acceptance. No pipeline or test suite was run
to write this plan, and no historical metric is treated as a current result.
All outcome values remain `[TBD]` until a pipeline run produces them in
`reports/metrics.json`.

## How to execute each phase

1. Owner records decisions in the relevant config and `OPEN-DECISIONS.md`.
2. Agent implements only the Section 10.1 plumbing for the active phase. Missing
   owner-written functions receive a signature, input/output/intent docstring
   and `raise NotImplementedError`; work stops at that dependency. Do not edit
   `src/evaluate.py` without an explicit request. Owner prose stays owner-written.
3. Run phase checks and `pytest`, including both guard tests. Run the pipeline
   for every reported outcome; all computed metrics go into `reports/metrics.json`.
4. Owner reruns checks, reviews the diff and explains the decisions without notes.
5. Use one PR per phase, record acceptance evidence and update roadmap checkboxes.
   Owner advances `AGENTS.md` only after the preceding phase passes.

Use the existing Python 3.11+ environment; on this machine the decision log
records a Python 3.9 default, so use `.venv\Scripts\python.exe` explicitly when
the environment is not activated. Do not add dependencies without owner approval.

Every phase preserves raw and earlier-stage tables, writes distinct outputs,
and uses deterministic seeds and fixed reference dates. Ground truth, including
both `rec_id` and `true_cluster_id`, belongs only in ingest and evaluation code.
Use opaque `unique_id` keys in matching, lineage and review outputs. Labels never
enter training or review screens; owner interpretation of evaluation results
must not become label-driven fitting or rule selection inside model code.

## Phase 0 — Setup and reproducible ingestion

**Owner:** approve dependency pins and confirm source ID parsing. Existing
decisions should be reused, not reopened without a reason.

- [ ] Confirm repo structure, pinned dependencies and Python environment.
- [ ] Inspect ingestion of source data, opaque keys and deterministic synthetic metadata.
- [ ] Preserve both leakage and raw-table guard tests.
- [ ] Run ingestion twice against isolated test databases and compare content.
- [ ] Confirm entity parsing and originals agree through permitted ingest/evaluation code.

**Outputs:** reproducible `raw_customers`, requirements and guard tests.
**Gate:** identical ingested content on repeated runs, verified entity parsing,
passing guards, and owner review of ingestion. This is verification of existing
work, not a request to rebuild it.

## Phase 1 — Profiling

**Owner:** write and defend the observed-problems list in
`reports/problems_observed.md`.

- [ ] Verify every column has null/blank rates, distinct counts, frequent values,
      lengths and format-pattern summaries.
- [ ] Keep ground-truth summaries in allowed code; profiling consumes their metrics.
- [ ] Generate `reports/profile.md` from measured metrics and embed the owner's
      observed-problems list.
- [ ] Check that at least five concrete problems have source examples and that
      every column has a completeness figure.

**Outputs:** profile report and owner-written problem list.
**Gate:** complete coverage, grounded examples, reproducible report and owner
explanation of which observations motivate Phase 2 rules.

## Phase 2 — Close out DQ rules and standardization (current)

**Owner inputs:** review open decision items 8, 11, 12 and 13. Confirm the
remaining DQ behavior and rulebook; settled mappings and field policies remain
settled. The ledger's reference to item 9 is stale and should be reconciled with
the recorded state-mapping decision, not treated as a fresh approval requirement.

- [ ] Reconcile historical ledger text that still describes empty rule lists or
      Phase 1 with the populated config and current Phase 2 status.
- [ ] Review item 13 assumptions: NULL/blank handling, usable-evidence counts,
      invalid-DOB reclassification, future dates, and config documentation.
      Change policy only following an owner decision.
- [ ] Owner determines how to present the synthetic age-band limitation (item 12).
      Keep broader review workflow and auto-merge questions explicitly deferred
      to the phases that need them.
- [ ] Verify configured transformations preserve source values, apply only
      approved corrections and handle null, empty and already-clean inputs.
- [ ] Verify raw/standardized DQ passes and separate age-review output; retain
      before/after violation counts in `reports/metrics.json`.
- [ ] Run the pipeline and full test suite, and compare repeated-run outputs.
- [ ] Owner reviews standardization edge cases and confirms rulebook section 1.

**Outputs:** `std_customers`, `dq_violations_raw`, `dq_violations_std`, age-review
table, config, tests and owner-confirmed DQ prose. No extra DQ Markdown report:
the owner already chose metrics-only reporting until Phase 7.
**Gate:** YAML-driven behavior, passing tests and guards, measured before/after
violations, reviewed assumptions and clear deferrals with no silent defaults.

## Phase 3 — Deterministic baseline and blocking

**Owner inputs:** baseline variants, candidate blocking rules, final blocking
choice and target pair completeness, plus treatment of DQ-ineligible records.
Owner writes `src/evaluate.py`, including pairwise metrics and pair completeness.

- [ ] Agree the eligible matching input and how invalid evidence is made
      unavailable; flags alone must not accidentally become valid matching inputs.
- [ ] Record baseline and blocking rules in YAML. Config layout for baseline
      rules must be agreed before implementation; no hard-coded rule values.
- [ ] Agent implements the baseline matcher and candidate counting over approved
      rules, with canonical unordered pairs and no self-pairs or duplicates.
- [ ] Owner implements and checks evaluation against hand-worked examples.
- [ ] Measure baseline precision/recall/F1, full pair count, candidate count,
      reduction ratio and pair completeness per block and for their union.
- [ ] Owner chooses and justifies final blocking rules in `config/blocking.yaml`
      and the rulebook, using the measured trade-off.

**Outputs:** baseline metrics, blocking analysis and approved blocking config.
**Gate:** measured baseline, correct evaluation, and owner-set blocking target
met with justified comparison reduction. Stop if evaluation is still a stub.

## Phase 4 — Probabilistic matching

**Owner inputs:** per-field comparisons and levels, term-frequency adjustments,
EM blocks, training/prior choices and error analysis. Owner understands m, u,
match weights and EM before approving the implementation.

- [ ] Verify API signatures against installed Splink 4.0.17 before coding;
      do not copy unverified v3 or newer-version calls.
- [ ] Agent wires approved settings, label-free input, prior estimation,
      random-sample u estimation and EM using at least two approved blocks.
- [ ] Predict blocked pairs; persist model settings and generate diagnostic charts.
- [ ] Owner's evaluator measures precision/recall/F1 across declared thresholds
      and compares with the baseline, using consistent evaluation scope.
- [ ] Check saved-model reproducibility and inspect training diagnostics.
- [ ] Owner explains an observed false positive and false negative with pair
      evidence and waterfall charts; if either is absent, report that honestly.

**Outputs:** saved model JSON, predictions, charts and `reports/model_evaluation.md`.
**Gate:** owner reviews all of `model.py`, explains the model without notes and
investigates failure to beat baseline F1 before advancing. No fabricated errors
or metrics to satisfy a checklist.

## Phase 5 — Thresholds, clusters and review queue

**Owner inputs:** lower/upper thresholds, equality at boundaries, acceptable
review workload, treatment of pending age reviews and a transitivity example.
Owner writes cluster evaluation in `evaluate.py`.

- [ ] Use measured curves and review-band volume to justify both thresholds;
      record policy in config and owner-written rulebook prose.
- [ ] Resolve whether pending age review blocks auto-merge (decision item 11).
- [ ] Agent wires connected-components clustering and explicit three-band routing.
- [ ] Produce a label-free pair review queue with probability and field evidence.
- [ ] Evaluate exact entity recovery, splits and erroneous merges through the
      owner evaluator; retain pairwise metrics alongside cluster metrics.
- [ ] Inspect transitive chains and owner explains a real example if present.
- [ ] Check threshold boundaries, singleton coverage and queue exclusions.

**Outputs:** `clusters`, `review_queue`, metrics and threshold justification.
**Gate:** measured threshold rationale/workload, cluster-level evaluation,
label-free review data and an explicit pending-age-review policy.

## Phase 6 — Survivorship and golden records

**Owner inputs:** every field rule in `config/survivorship.yaml`, source ranking,
tie-breakers, invalid-value handling and all-null behavior. Roadmap examples
are options, not adopted rules.

- [ ] Owner completes policy for each output field and every tie/fallback case.
- [ ] Agent implements the configured engine over approved clusters.
- [ ] Write one golden record per cluster and field-level source/rule lineage.
- [ ] Test small hand-built clusters with conflicts, ties, invalid values and
      all-null fields against owner-specified outcomes.
- [ ] Check deterministic winners and complete lineage, including the agreed
      explanation of fields with no usable value.
- [ ] Owner reviews engine logic, tie handling and survivorship rulebook prose.

**Outputs:** `golden_records`, `golden_lineage`, config and tests.
**Gate:** every output field has auditable provenance or the explicitly approved
null outcome; ties/all-null cases pass and repeated runs choose identical winners.

## Phase 7 — Scorecard and reproducible delivery

**Owner inputs:** scorecard definitions/denominators, rulebook prose, README
results and limitations. Clarify raw-record versus golden-entity comparison so
reduced row counts are not automatically described as improved quality.

- [ ] Agent formats before/after record count, duplicate rate, key-field
      completeness and per-rule validity from `reports/metrics.json` only.
- [ ] Complete one-command orchestration through scorecard generation.
- [ ] Agent supplies README structure/diagram; owner writes results and limitations.
- [ ] Owner explains synthetic source/timestamps, dataset limits, age-review
      behavior and remaining assumptions without overstating production readiness.
- [ ] Run tests and a fresh-clone install/pipeline reproduction with approved pins.
- [ ] Compare metrics and data content with a second run; inspect report numbers
      against the metrics produced in this run.
- [ ] Owner checks all published numbers and explains the roadmap interview topics.

**Outputs:** reproducible repository, scorecard, complete README and rulebook.
**Gate:** one command reproduces results from a fresh clone; all checks pass;
a non-technical reader can understand the rules. Core project ends here.

## Phase 8 — Optional stewardship UI

Start only after core acceptance and an explicit owner choice to pursue the UI.
**Owner inputs:** API design, decision-log schema, storage choice, reviewer
workflow, conflicting/reversed decisions and feedback semantics. Approve any
new dependencies before installing them.

- [ ] Agree API contracts and audit schema before implementation.
- [ ] Agent builds Spring Boot endpoints and React side-by-side review with
      differences highlighted and approve/reject actions.
- [ ] Persist reviewer, timestamp, outcome and comment in a retrievable audit log.
- [ ] Feed approved decisions into new clustering/survivorship outputs while
      preserving earlier stage data and decision history.
- [ ] Verify the agreed behavior for rejection, repeated submissions and reruns.
- [ ] Test a UI decision through to the resulting golden record and its lineage.
- [ ] Owner reviews the feedback loop. Review-band evaluation is a separate
      stretch step, using actual steward decisions and the owner evaluator.

**Outputs:** working UI/API, decision log and verified feedback loop.
**Gate:** an accepted UI merge changes the appropriate golden output after a
rerun, every decision is retrievable, and no ground truth reaches the UI.

## Immediate work order and scheduling

1. Close Phase 2 assumptions and verify its outputs/tests.
2. Obtain owner acceptance of Phase 2 and advance the phase explicitly.
3. Agree Phase 3 rules and the evaluation interface; owner writes evaluation.
4. Work through Phases 3–7 sequentially, one reviewed phase at a time.
5. Decide on Phase 8 and only then consider other stretch work.

Use the roadmap's effort estimates for scheduling; they are estimates, not
deadlines or measured progress. Owner decision/evaluation time is a dependency,
especially for Phases 3–6. Do not compress review to meet the suggested timeline.
Febrl 4 linkage, alternate synthetic data and incremental matching remain
separate, optional scopes after the core is accepted.

At each handoff report files changed, actual acceptance commands/results,
uncertainties (including unverified APIs), owner stubs and decision-log updates.
