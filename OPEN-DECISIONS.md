# Open decisions

Things the agent needs from the owner, and the decisions already made. The agent
adds to this file whenever it hits a choice that belongs to the owner
(`AGENTS.md`, "Owner-owned decisions"), or makes an assumption to keep moving.

**Owner:** Manish Manoj Nair · **Last updated:** 2026-10-01 (Phase 2 review findings fixed and verified; items 12 and 13 still await the owner)

- **Open** — waiting on you. The agent has assumed something in the meantime;
  each entry says what.
- **Decided** — settled. Kept so the reasoning survives, because interview
  questions come from this list.

---

## Open

### 8. Every Phase 2 rule, and which fields are mandatory — settled; one piece belongs to Phase 3

Discussion on 2026-09-28: first define what "usable" means for this project
(retained for identity resolution, eligible for automatic matching, or ready for
a business use such as mailing). These need not share mandatory fields. The
policy was selected on 2026-09-29, below.

Working definition from the owner on 2026-09-29: a usable customer record must
contain enough information to clearly identify and differentiate a unique
customer, without relying on unnecessary features that make identification more
burdensome. The owner's decision below turns this into the executable rule:
usability is admission to matching, and the minimum is three independent
identity signals.

Owner decision on 2026-09-29: a missing `given_name` does not by itself make a
record ineligible for matching. A record containing surname, date of birth and
postcode is considered to have useful identifying evidence. `given_name` is not
therefore a mandatory field, but remains optional supporting evidence. The
minimum set is the three primary features `surname`, `date_of_birth` and
`postcode`; `soc_sec_id` may replace one missing primary feature. Because one
secondary feature cannot replace two missing primary features, a record with two
missing primary features is ineligible under this rule. An impossible date of
birth counts as unavailable in the same way as a missing value: preserve and
flag the source value, but exclude it from identity evidence.

*Status, reconciled 2026-10-01.* The rules are written. `config/dq_rules.yaml`
holds DQ-C-001 to DQ-C-004 and DQ-V-001 to DQ-V-004: each condition is flagged by
its own rule, and DQ-C-004 decides record-level eligibility. The rest of the
policy is recorded under Decided (matching eligibility, severity, optional
fields, identifier errors). The starting material was P1–P8 in
`reports/problems_observed.md`.

*Still open, and not needed to close Phase 2:* the exact treatment of a record
that fails DQ-C-004. Phase 3 has to say what the matching input does with it:
excluded from candidate pairs, kept but never auto-merged, or routed to review.
It is listed in `WORKING-PLAN.md` as a Phase 3 input and gets its own Open entry
when Phase 3 starts.

*Assumed:* nothing. DQ-C-004 only flags the record; it stays in `std_customers`
and nothing downstream drops it.

### 11. What does the stricter verification process do for extreme ages?

The owner selected two enhanced-review bands: completed age under 18 and age 100
or older. Records in either band should be available in a separate review table.
Age must be calculated against a fixed reference date so repeated runs do not
change merely because the current date changed.

Owner rationale for the younger band: minors can face distinct consent and
identity-verification requirements and may have fewer standard identity
documents. This means a different, age-appropriate verification path rather than
automatic invalidation or a presumption of greater risk. Australian guidance
makes the exact process context-dependent: the Privacy Act has no single age of
consent and capacity is assessed case by case, while AUSTRAC supports risk-based
alternative identity procedures when standard documents are unavailable. The
precise business domain is therefore still needed.

Evidence for the minor pathway is settled: accept a birth certificate or birth
extract, a current student card, or a recent school-principal letter containing
the minor's name, residential address and attendance information. If those are
unavailable, use a documented referee process appropriate to the customer's
circumstances. Do not collect vaccination records solely for identity
verification because they expose health information beyond what this purpose
requires.

Severity policy is settled: one missing primary identity feature is a warning
because `soc_sec_id` can substitute; two missing or unusable primary features is
an error; an impossible DOB is an error and unavailable for matching; an invalid
state code before an approved correction is a warning; and a missing
`given_name` is not a violation because it is optional.

Text-normalization policy is settled for `given_name`, `surname`, `address_1`,
`address_2` and `suburb`: trim surrounding whitespace, collapse repeated internal
whitespace and lowercase letters. Preserve apostrophes, hyphens, word order and
the words themselves. Do not correct spelling or expand abbreviations without a
separate explicit mapping.

DOB-standardization policy is settled: preserve `date_of_birth`; parse valid
`%Y%m%d` values into an ISO `date_of_birth_std` value formatted `%Y-%m-%d`; set
the standardized value to NULL when the source is missing or fails strict
calendar parsing; record impossible dates as errors; and calculate age only from
the standardized date using a fixed reference date.

Postcode and identifier policy is settled: trim surrounding whitespace; require
exactly four digits for `postcode` and seven digits for `soc_sec_id`; treat a
value that fails its observed format as unavailable for identity matching;
preserve and flag the source value; and do not strip internal punctuation or
letters because doing so could turn corruption into a plausible identifier.

Address abbreviation mappings are settled for whole words: `vlge → village`,
`locn → location`, `mt → mount`, `hse → house`, `flr → floor`, and `unt → unit`.
`st` is expanded contextually: at the beginning of an address component it means
`saint`; elsewhere it means `street`; and the exact adjacent tokens `st reet`
become the single word `street`. Inspection shows this handles every observed
context and avoids maintaining a subjective dictionary of "Christian first
names."

Completeness policy for the remaining customer fields is settled: `given_name`,
`street_number`, `address_1`, `address_2`, `suburb` and `state` are optional.
Their missingness remains visible in profiling but does not itself create a DQ
violation or make a record unusable. A supplied optional value can still violate
a validity rule, and every optional field may contribute supporting match
evidence when present.

Invalid-format `postcode` and `soc_sec_id` values are field-level errors. They do
not automatically make the whole record unusable; the composite identity-evidence
rule separately evaluates whether three usable signals remain after invalid and
missing values are treated as unavailable.

Age is calculated as completed years on the fixed reference date 2026-09-22 for
both review bands. This matches the project's synthetic metadata reference date
and keeps results deterministic across runs.

Age-review routing is settled for Phase 2: a calendar-valid DOB remains identity
evidence; the customer stays in `std_customers` and remains eligible for matching;
and a separate table references the record by `unique_id` with calculated age,
fixed calculation date, reason (`minor_verification` or `age_100_plus`) and an
initial `pending` status. The table references rather than duplicates the
customer record. Whether a pending review blocks automatic merging is deferred
to the Phase 5 threshold decision.

Deferred, none of it needed for Phase 2 (reconciled 2026-10-01: eligibility for
ordinary matching while review is pending is settled above and in Decided, so it
is no longer listed as open): whether a pending review blocks *automatic merging*
(Phase 5, with the thresholds); which evidence the 100+ pathway examines; and
what review outcomes are recorded (before any review workflow is built). An
extreme age alone does not establish death, staleness or identity fraud; those
are possible investigation hypotheses rather than DQ findings.

External research supports the threshold as a review signal. AIHW estimates
6,181 Australians aged 100+ in 2022, or 238 per million residents (0.0238%). The
research is summarized in `reports/Centenarian prevalence and review.md`.
Project-specific age counts and comparison ratios remain `[TBD]` in that report
until the pipeline produces them in `reports/metrics.json` during a run.

### 12. The 100+ band is very large on this dataset, and the minor band is empty

*Raised by the agent, 2026-09-29.* A scratch run of the full pipeline (numbers
are in `reports/metrics.json` under `age_review.*` after `python run_pipeline.py`;
none are quoted here) shows the standardized DOBs span 1900-01-03 to 1999-12-12.
Febrl generates birth years uniformly, so against the fixed reference date the
`age_100_plus` band captures roughly a quarter of all records, and
`minor_verification` captures none because nobody is born after 2008. This
conflicts with the premise in item 11 that age 100+ is statistically exceptional
(the AIHW figure is about 0.02%), so on this synthetic data the band is a property
of how Febrl was generated, not a signal.

*Assumed:* nothing changed. The bands run exactly as written and flag whoever
falls in them. Your call: keep the bands as a policy demonstration and say so in
the README limitations, change the 100+ threshold, or treat this as a reason to
document that the review rule is exercised only by unit tests on the minor band.

### 13. Agent choices made while implementing the Phase 2 rules

*Assumed, overrule any of them:*

- `present` is the one completeness check that fails on NULL; a blank
  (whitespace-only) string also fails it. Every other check still passes NULL.
  A string that is blank after trimming stays an empty string rather than becoming
  NULL, so it fails `present` and is *also* a value to the validity rules (a blank
  postcode would raise DQ-C-003 and DQ-V-002). Not observed: a query of
  `raw_customers` on 2026-10-01 found no blank string in any column.
- `DQ-C-004` (`minimum_identity_evidence`) counts a signal as usable only when
  the value is non-NULL **and** passes its `usable_when` check. `soc_sec_id`
  contributes at most `max_substitutes` signals. The value recorded in
  `dq_violations_*` for this rule is the text `usable_signals=<n>`.
- `standardized_format` is used instead of `format` whenever a rule reads a
  `<field>_std` column, so `DQ-V-001` reads the raw DOB as `%Y%m%d` and the
  cleaned one as `%Y-%m-%d`. Because the cleaned DOB is NULL when impossible,
  `DQ-V-001` reports zero in the cleaned pass and `DQ-C-002` rises by the same
  records: the impossible DOBs are reclassified as missing, by design.
- `on_error: null` in `dq_rules.yaml` loads as YAML null, not the string `"null"`;
  `normalize_date` accepts both. The config was not edited.
- Age is completed years from `date_sub('year', dob, reference)`. A DOB after the
  reference date gives a negative age and is in no band, and no rule flags it.
  Not observed in the data; say if you want a rule for it.
- `age_review` is a separate stage after `dq_std`. Its metrics are
  `age_review.reference_date`, `.flagged_count` and `.flagged_by_reason`.
- The header of `config/dq_rules.yaml` lists the check and transform types
  without `present`, `minimum_identity_evidence`, `replace_phrases` or
  `replace_contextual_word`. The config is owner-authored, so it was not edited.

*Added 2026-10-01 while fixing the review findings. These are how the engine reads
policy you already settled; none changes a rule's meaning on this data (a run
before and after the fix gave the same metrics apart from one new config echo,
`age_review.output_table`).*

- **"Whitespace" means any whitespace, not only spaces.** Trim, collapse and the
  `present` / `not_blank` / `in_set` checks all use ASCII whitespace plus Unicode
  separators such as the non-breaking space (`dq_rules.WHITESPACE`). DuckDB's own
  `TRIM` strips spaces only, so a tab-padded value used to survive "trim" and a
  tab-only surname used to count as present.
- **A date is valid only if it is exactly what the format writes.** DuckDB's
  parser reads `1970011` as 1970-01-01 and tolerates padding, which would invent a
  date the source never held. `DQ-V-001`, the DOB signal in `DQ-C-004` and
  `normalize_date` now accept a value only if re-formatting the parsed date
  reproduces it, so a seven-digit or padded DOB is invalid and becomes NULL.
- **A padded DOB is invalid, not trimmed.** The config has no `trim` step before
  `normalize_date` on `date_of_birth`, and the policy says an unparseable source
  becomes NULL, so `' 19700101'` is treated as unusable. Not observed in the data
  (every DOB is NULL or exactly eight digits). Add a `trim` step to the DOB chain
  if you would rather accept padded dates.
- **Age-review output is protected.** `output_table` may not be `raw_customers`,
  `std_customers` or any `dq_violations_*` table, and the stage refuses to replace
  an existing table that does not have its own columns (so it cannot overwrite a
  later phase's table either). Before the fix, `output_table: raw_customers`
  silently replaced the raw table.
- **A switched-off or renamed age review cleans up after itself.** With no
  `age_review:` section the stage drops its earlier output table and removes its
  `age_review.*` metrics; renaming the output drops the old table. It only drops a
  table that has exactly the age-review columns, whatever name a metrics file
  claims. New helper: `ingest.remove_metrics`.
- `RULEBOOK.md` was not edited (owner-written). Its §1.2 and §1.4 say "a real
  calendar date in `YYYYMMDD`" and "trim surrounding whitespace"; the engine now
  enforces those literally. Add a sentence if you want strictness spelled out.

---

## Needed before the next phase

Review update (2026-09-29): targeted review reproduced five gaps in raw-table
preservation, age-review output name protection, strict DOB format validation,
surrounding-whitespace handling, and stale outputs when age review is disabled.
**Fixed 2026-10-01**, each reproduced first and now covered by a regression test
that fails against the old code (the tests are in `tests/test_dq_rules.py`,
`tests/test_standardize.py` and `tests/test_phase2_rules_config.py`; the two guard
tests were not touched). The behaviour is described under item 13, "Added
2026-10-01". These were implementation findings against existing contracts; no
owner policy was selected or changed.

Planning update (2026-09-29): `WORKING-PLAN.md` sequences all phases and their
owner/agent handoffs. Planning does not advance the current phase or settle any
open policy. Reconciliation done 2026-10-01: item 8's historical text now matches
the populated config and Phase 2, and the stale item 9 reference is gone (the
state-correction decision is under Decided). Item 11's auto-merge question
belongs to Phase 5; broader review-workflow details must be settled before their
implementation. Future phase decisions are listed in the working plan and should
receive individual Open entries when those phases require owner input. No new
default is assumed.

**Phase 2 — DQ rules.** The engine, check types, transforms, age-review stage and
their tests are in place (`src/dq_rules.py`, `src/standardize.py`,
`src/age_review.py`). Remaining for you: answer items 12 and 13 (the age-band
presentation, and whether to keep or overrule the agent's assumptions), and
confirm `RULEBOOK.md` section 1. Then advance the phase in `AGENTS.md`.

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
| 2026-09-26 | Accept `ingest.cluster_size_distribution` in `ingest.py` | Only ingest/evaluate may group by ground truth (rule 1); profile.py reads it back from metrics.json |
| 2026-09-26 | "Duplicate rate" = duplicate records ÷ total records; "average records per entity" = records ÷ entities | Standard DQ meaning; both reported, under separate names |
| 2026-09-26 | Record-ID format confirmed: `rec-<N>-org` / `rec-<N>-dup-<k>`, `<N>` = entity | Verified by owner in DuckDB: 5,000 rows / 2,000 entities; 0 IDs outside the pattern in the raw CSV; exactly one `-org` per entity; `true_cluster_id` matches `<N>` in all rows |
| 2026-09-27 | Dependency pins accepted as installed on 2026-09-22 | `pandas==2.3.3`, `duckdb==1.5.5`, `splink==4.0.17`, `recordlinkage==0.16`, `PyYAML==6.0.3`, `pytest==9.1.1`. Splink v4 API only |
| 2026-09-27 | Ingest constants (`RANDOM_SEED`, `LAST_UPDATED_REFERENCE_DATE`, 3-year window) stay in `src/ingest.py` | They aren't DQ, blocking or survivorship rules, which is what the config rule covers |
| 2026-09-27 | Keep `data/raw/febrl3.csv` tracked in git | Makes the input inspectable on GitHub; `.gitattributes` keeps it byte-identical across clones |
| 2026-09-27 | One pull request per phase | Gives a diff to review against the roadmap §10.4 checklist |
| 2026-09-27 | The problems list lives in `reports/problems_observed.md`; `profile.py` embeds it verbatim at the end of `profile.md` | `profile.md` is regenerated on every run, so any hand edit to it was lost. The owner edits only the separate file; the generated report still has the "Problems observed" section the roadmap §5 deliverable asks for. `[TBD]` if the file is missing |
| 2026-09-27 | Rules use **named check types**, not raw SQL and not Python callables | `{type: in_set, values: [...]}` reads as a rule rather than as code, keeps config out of the SQL parser, and still means a new rule needs no code change. A new *kind* of check does, which is the intended trade |
| 2026-09-27 | The agent scaffolds Phase 2, the owner authors the rules | Engine, check types, transforms and tests from the agent; `config/dq_rules.yaml` content and `RULEBOOK.md` prose from the owner (`AGENTS.md` hard rule 5) |
| 2026-09-29 | Matching eligibility uses three identity features | Primary set: surname, date of birth and postcode. `soc_sec_id` replaces one missing or invalid primary feature. Given name is optional supporting evidence. A DOB that fails strict `%Y%m%d` calendar parsing is unavailable but remains preserved and flagged. Counts under this rule are `[TBD]` until produced by the pipeline in a run. |
| 2026-09-29 | Age-based review bands are under 18 and 100+ | Route minors to a different, age-appropriate consent and identity-verification path; do not treat minority itself as invalid or suspicious. Route age 100+ to enhanced review because it is statistically exceptional, without inferring death, fraud or staleness. Project counts are `[TBD]` until produced by the pipeline in a run. The precise business domain, review workflow and effect on matching remain open. |
| 2026-09-29 | Evidence accepted for the minor-review pathway | Accept a birth certificate/extract, current student card, or recent school-principal letter containing name, residential address and attendance information. If unavailable, use a documented referee process appropriate to the circumstances. Exclude vaccination records from identity verification to avoid collecting unnecessary health information. |
| 2026-09-29 | Invalid state codes are flagged in raw data and corrected through explicit mappings | Preserve the source value, flag it in the raw DQ pass, and map only these owner-approved values during standardization: `nws/nsq/nss/nxw/nhw/nse/nsh/nsy → nsw`; `vci/vid/sic/viv/vix/vkc → vic`; `qdl/qls/qlf/qkd/qle → qld`; `aw/wq/ws → wa`; `ss/as → sa`; `nf → nt`; `sct → act`; `tsa → tas`. The owner judged `as` most likely South Australia and `tsa` most likely Tasmania. The standardized pass should no longer flag these mapped values, while the original columns retain the supplied codes. |
| 2026-09-29 | DQ severity follows matching usability | One missing primary feature is a warning; two missing or unusable primary features is an error; impossible DOB is an error and unavailable for matching; raw invalid state is a warning; missing given name is allowed and produces no violation. |
| 2026-09-29 | Name and address text receive representation-only normalization | For `given_name`, `surname`, `address_1`, `address_2` and `suburb`: trim, collapse repeated whitespace and lowercase. Preserve punctuation, word order and spelling unless a later explicit mapping is approved. |
| 2026-09-29 | Invalid DOBs become unavailable in standardized data | Preserve the source DOB; normalize valid `%Y%m%d` dates to `%Y-%m-%d`; set invalid or missing standardized DOBs to NULL; record impossible dates as errors; derive age only from valid standardized dates against a fixed reference date. |
| 2026-09-29 | Postcode and `soc_sec_id` retain only safe representation changes | Trim surrounding whitespace and validate against the observed formats: four digits for postcode and seven for `soc_sec_id`. Preserve and flag invalid source values, make them unavailable for identity matching, and do not remove internal non-digits automatically. |
| 2026-09-29 | Address abbreviations receive explicit contextual expansion | Map whole words `vlge → village`, `locn → location`, `mt → mount`, `hse → house`, `flr → floor`, and `unt → unit`. At the start of an address component map `st → saint`; elsewhere map `st → street`; collapse the exact split `st reet → street`. Do not use unrestricted substring replacement. |
| 2026-09-29 | Non-primary customer fields are optional | Missing `given_name`, `street_number`, `address_1`, `address_2`, `suburb` or `state` remains a profile metric rather than a DQ violation. Supplied values are still subject to validity rules and can provide supporting match evidence. |
| 2026-09-29 | Identifier format errors are separate from record usability | An invalid-format postcode or `soc_sec_id` is an error and becomes unavailable as identity evidence. The composite rule independently determines whether the record still has three usable identity signals. |
| 2026-09-29 | Age calculations use the fixed date 2026-09-22 | Calculate completed age against the same reference date used for synthetic metadata. Do not use the pipeline run date, because review-band membership must be reproducible. |
| 2026-09-29 | Age review runs alongside entity matching | Keep valid DOBs as identity evidence and keep flagged records eligible for matching. Write a separate reference-based review table with `unique_id`, calculated age, fixed calculation date, reason and initial `pending` status. Decide any auto-merge restriction in Phase 5. |
| 2026-09-29 | `metrics.json` is sufficient Phase 2 reporting | Store before/after violation counts under the existing `dq.raw.*` and `dq.std.*` keys. Do not add a separate Markdown DQ report; the readable scorecard belongs to Phase 7. |

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

Phase 2 (`src/dq_rules.py`, `src/standardize.py`):

- **NULL passes every check except `not_null` and `present`.** A missing value is
  one completeness violation, not one for every validity rule that reads the
  field. A field is mandatory only if you give it a `not_null` or `present` rule.
- **The DQ stage never changes data.** It records the record, rule, field,
  dimension, severity and offending value; no row is dropped and no value is
  corrected. Correction is standardization, and it is opt-in per field.
- **Two violations tables, not one:** `dq_violations_raw` and
  `dq_violations_std`, one per pass. The roadmap names a single `dq_violations`
  table, but one table per pass keeps the before/after counts side by side
  without either overwriting the other (architecture rule 1).
- **In the cleaned pass a rule reads `<field>_std` when that column exists**, so
  the same rule id gives the before and after number for the same field.
- `std_customers` carries `unique_id`, the ten source fields and the two
  synthetic columns — **not** the ground-truth columns, which stay in
  `raw_customers` for `evaluate.py` to join back on `unique_id` (hard rule 1).
- `in_set` compares case-insensitively and ignores surrounding space unless a
  rule sets `case_sensitive: true`; the data is lower-case today, so this only
  decides what happens if that changes.
- `normalize_date` uses `on_error: null` for DOB. The original source column and
  raw violation preserve the evidence, while the standardized NULL ensures an
  impossible date cannot contribute matching evidence. It parses strictly: only a
  value exactly in `from_format` becomes a date.
- `replace_words` matches whole words and applies its mapping in the order
  written, so the output stays reproducible (architecture rule 4).
