# Rulebook

Every rule this pipeline applies, in plain English, so the behaviour can be
explained without reading code. The machine-readable source of truth is
`config/dq_rules.yaml`, `config/baseline.yaml` and `config/blocking.yaml`;
this file says what each rule means and **why it exists**.

Owner-written (`AGENTS.md`: anything in `RULEBOOK.md` is an owner decision). One
entry per rule, matching its `id` in the config, so the two can be read side by
side. Section 2 covers the Phase 3 baseline and blocking. Later phases add
matching and survivorship sections.

---
## 1. Data-quality rules (Phase 2)

The purpose of these rules is to determine whether each record contains enough
usable evidence for entity resolution while preserving every supplied source
value. A violation never changes or deletes the raw record.

### 1.1 Completeness — which fields make a record usable

A usable record needs three independent identity signals. The primary signals
are surname, date of birth and postcode. A valid `soc_sec_id` may replace one
missing or invalid primary signal, but it cannot replace two.

Given name is optional. It can strengthen a match when present, but its absence
does not make a record unusable. Street number, both address lines, suburb and
state are also optional. Their completeness is measured in the profile, but
their absence is not a DQ violation.

| Rule | Field | What it requires | Why |
|---|---|---|---|
| DQ-C-001 | `surname` | A surname should be present. | Surname is one of the three primary identity signals. One missing primary signal is a warning because `soc_sec_id` may substitute. |
| DQ-C-002 | `date_of_birth` | A date of birth should be present. | DOB is one of the three primary identity signals. One missing primary signal is a warning because `soc_sec_id` may substitute. |
| DQ-C-003 | `postcode` | A postcode should be present. | Postcode is one of the three primary identity signals. One missing primary signal is a warning because `soc_sec_id` may substitute. |
| DQ-C-004 | Record-level identity evidence | Three usable identity signals must remain, with `soc_sec_id` replacing no more than one primary signal. | A record with fewer than three usable signals does not contain enough evidence for reliable identity resolution. |

A field-level warning or error does not automatically decide whether the whole
record is usable. DQ-C-004 makes that decision from the usable evidence that
remains.

### 1.2 Validity — what a supplied value must satisfy

| Rule | Field | What counts as valid | Why |
|---|---|---|---|
| DQ-V-001 | `date_of_birth` | The raw value parses as a real calendar date in `YYYYMMDD`; the standardized value parses as `YYYY-MM-DD`. | Eight digits can still describe an impossible date. An impossible DOB is unavailable for matching. |
| DQ-V-002 | `postcode` | Exactly four digits. | This is the only postcode format observed in the source data. Internal punctuation or letters are not silently removed. |
| DQ-V-003 | `soc_sec_id` | Exactly seven digits. | This is the only identifier format observed in the source data. Internal punctuation or letters are not silently removed. |
| DQ-V-004 | `state` | One of `nsw`, `vic`, `qld`, `sa`, `wa`, `tas`, `nt`, or `act`. | A supplied state outside the accepted Australian codes is invalid, although an approved explicit correction may standardize it. |

Invalid postcode and `soc_sec_id` values are field-level errors and become
unavailable as identity evidence. Record usability is still evaluated separately
by DQ-C-004.

### 1.3 Age-review routing

Age is calculated in completed years against the fixed date 2026-09-22. Using a
fixed date keeps repeated pipeline runs deterministic.

A calendar-valid DOB implying an age under 18 creates a
`minor_verification` review item. The purpose is to determine the
age-appropriate consent and identity-verification path. Minority is not itself
invalid or suspicious.

Accepted evidence for the minor pathway includes:

- a birth certificate or birth extract;
- a current student card;
- a recent school-principal letter containing the minor's name, residential
  address and attendance information; or
- when ordinary documents are unavailable, a documented referee process
  appropriate to the customer's circumstances.

Vaccination records are not collected solely for identity verification because
they expose health information beyond what this purpose requires.

A calendar-valid DOB implying an age of 100 or older creates an `age_100_plus`
review item. This is a neutral review flag. It does not classify the customer as
deceased, stale, fraudulent, or a victim of identity theft without independent
evidence.

Age-review records remain in `std_customers`, remain eligible for matching, and
retain their valid DOB as identity evidence. The separate review table references
the customer by `unique_id` and records the calculated age, calculation date,
reason and initial `pending` status. Whether pending review blocks automatic
merging is a Phase 5 threshold decision.

### 1.4 Standardization — how values are normalized

Every standardized value is written beside the original source value. The raw
value is never overwritten.

| Field | Steps | Why | What it deliberately does not do |
|---|---|---|---|
| `given_name`, `surname` | Trim, collapse repeated whitespace, lowercase. | Normalize representation without changing identity. | Does not remove punctuation, change word order, or correct spelling. |
| `address_1`, `address_2` | Trim, collapse whitespace, lowercase, expand approved whole-word abbreviations, and apply the contextual `st` rule. | Bring equivalent address representations closer together. | Does not generally correct misspelled street names or suffixes. |
| `suburb` | Trim, collapse repeated whitespace, lowercase. | Normalize representation. | Does not correct spelling. |
| `state` | Trim, lowercase, then apply the approved explicit value mappings. | Correct only state-code errors reviewed by the owner. | Does not infer state from postcode or select a value through automatic edit distance. |
| `date_of_birth` | Trim surrounding whitespace, then strictly parse `YYYYMMDD` and output `YYYY-MM-DD`; output null when parsing fails. | Give valid dates one representation and prevent impossible dates from contributing match evidence. | Preserves the source DOB; does not remove internal whitespace or guess the intended date. |
| `postcode`, `soc_sec_id` | Trim surrounding whitespace. | Remove harmless surrounding spacing. | Does not strip internal punctuation or letters. |

Approved address expansions are:

- `vlge → village`
- `locn → location`
- `mt → mount`
- `hse → house`
- `flr → floor`
- `unt → unit`
- `st reet → street`
- `st → saint` at the beginning of an address component
- `st → street` elsewhere

Approved state corrections are:

- `nws`, `nsq`, `nss`, `nxw`, `nhw`, `nse`, `nsh`, `nsy → nsw`
- `vci`, `vid`, `sic`, `viv`, `vix`, `vkc → vic`
- `qdl`, `qls`, `qlf`, `qkd`, `qle → qld`
- `aw`, `wq`, `ws → wa`
- `ss`, `as → sa`
- `nf → nt`
- `sct → act`
- `tsa → tas`

The `as → sa` and `tsa → tas` corrections are explicit owner decisions. Their
source values remain available for audit.

### 1.5 Conventions the engine applies

- Missing values do not also violate every validity rule that references the
  field.
- Severity is recorded rather than acted upon. Both errors and warnings leave
  the source row intact.
- Rules are evaluated against raw and standardized data so before-and-after
  counts remain comparable.
- Standardized columns are preferred during the cleaned pass.
- Invalid or missing evidence is excluded from the composite usability check.
- No rule uses `rec_id` or `true_cluster_id`.
- All project metrics are written to `reports/metrics.json`.

---

## 2. Deterministic baseline and blocking (Phase 3)

Owner approved the final blocking set and authorized this section on 2026-10-02.
Rules live in `config/baseline.yaml` and `config/blocking.yaml`. All measured
values below come from `reports/metrics.json`, regenerated by the pipeline on
2026-10-02. These tables are a snapshot and must be refreshed after rule changes.

### 2.1 Matching input and unavailable evidence

The pipeline builds `matching_customers` from standardized data. It carries
opaque record IDs and configured standardized fields, retaining every record.
Values flagged by standardized validity checks become NULL in this separate
table. The raw data, standardized values and violation evidence remain intact.
Two missing values never count as agreement; empty strings also provide no
agreement. A remaining flagged-invalid value causes matching to stop.

Records failing DQ-C-004 still participate in baseline matching and blocking.
The approved policy prohibits automatic merging for pairs involving them and
routes those pairs to review in Phase 5. Phase 3 does not perform those merges
or build that review workflow.

### 2.2 Baseline rules and results

Each variant declares a match only when every listed standardized field agrees
exactly and is present. The variants are measured separately; their outputs are
not combined into a fourth baseline.

| Rule ID | Plain-English rule | Why test it? |
|---|---|---|
| `surname_dob_postcode` | Two records match when standardized surname, date of birth and postcode are all equal. | Strict reference requiring agreement on all three primary fields. |
| `surname_dob` | Two records match when standardized surname and date of birth are equal. | Remove postcode to test how many matches postcode disagreement or missingness prevents. |
| `dob_postcode` | Two records match when standardized date of birth and postcode are equal. | Remove surname to test how many matches surname disagreement or missingness prevents. |

| Variant | Declared pairs | Precision | Recall | F1 |
|---|---:|---:|---:|---:|
| `surname_dob_postcode` | 2,425 | 100.00% | 37.09% | 54.11% |
| `surname_dob` | 3,106 | 100.00% | 47.51% | 64.41% |
| `dob_postcode` | 4,343 | 100.00% | 66.43% | 79.83% |

Both relaxed variants recover more true pairs without any observed false
positives on this dataset. The experiment therefore shows increased recall
without a measured precision loss; it does not establish that looser exact
matching always preserves precision. DOB plus postcode has the highest measured
F1 among these variants, but exact agreement still misses true pairs. These
synthetic-data results are not a guarantee of performance on new customer data.

### 2.3 Final blocking rules

Blocking selects pairs for later comparison; it does not declare them matches.
Keep a pair when any of the following four rules accepts it. Remove overlaps
so a pair appearing under several rules is compared only once.

| Rule ID | Plain-English rule | Why retain this route? |
|---|---|---|
| `surname` | Records with the same standardized surname are candidates. | Provides a route when surname survives but DOB or location evidence differs. |
| `date_of_birth` | Records with the same standardized date of birth are candidates. | Provides a route when DOB survives despite name or location differences. |
| `postcode_given_initial` | Records with the same postcode and the same first letter of given name are candidates. | Provides a route using location and a short name prefix rather than a full name or DOB. |
| `soc_sec_id` | Records with the same valid standardized social security identifier are candidates. | Provides an identifier route when names, DOB or postcode differ. Format-valid agreement creates a candidate, not proof of identity. |

| Blocking rule | Candidate pairs | Pair completeness | Reduction ratio |
|---|---:|---:|---:|
| `surname` | 37,255 | 54.94% | 99.70% |
| `date_of_birth` | 5,966 | 86.46% | 99.95% |
| `postcode_given_initial` | 4,300 | 56.97% | 99.97% |
| `soc_sec_id` | 5,601 | 85.67% | 99.96% |
| **Final union** | **41,057** | **99.59%** | **99.67%** |

The owner-set completeness target is 99.00%. The final union
retains 99.59% of true duplicate pairs while generating
41,057 candidates instead of 12,497,500 possible pairs.
This meets the target while reducing comparisons by more than two orders of
magnitude. All four rules are retained as the approved balance of coverage and
comparison cost. The analysis does not establish that this is the smallest or
cheapest possible subset. Individual rule completeness values overlap and must
not be added together.

### 2.4 Evaluation definitions and limits

- Precision is TP / (TP + FP): the share of declared matches that are correct.
- Recall is TP / (TP + FN): the share of all true pairs recovered.
- F1 is 2TP / (2TP + FP + FN).
- Pair completeness is true pairs surviving blocking divided by all true pairs.
- Full comparisons are n(n-1)/2; reduction ratio is 1 minus candidate pairs divided by full comparisons.
- A ratio with a zero denominator is undefined and stored as JSON null. With true pairs but no predictions, recall and F1 are zero and precision is undefined.

Ground truth is used only by evaluation, joined through opaque IDs. The reference
population includes all raw records, including true pairs absent from candidate
tables. Pairs are unordered, unique and never self-pairs.

Pair completeness is the recall ceiling for a model restricted to this candidate
set. Later scoring can reject true candidates but cannot recover a pair excluded
by blocking. Blocking choices were assessed on this labeled synthetic dataset;
a separate dataset would be needed to assess generalization.
