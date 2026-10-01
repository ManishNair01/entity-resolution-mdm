# Rulebook

Every rule this pipeline applies, in plain English, so the behaviour can be
explained without reading code. The machine-readable source of truth is
`config/dq_rules.yaml`; this file says what each rule means and **why it exists**.

Owner-written (`AGENTS.md`: anything in `RULEBOOK.md` is an owner decision). One
entry per rule, matching its `id` in the config, so the two can be read side by
side. Later phases add their own sections — blocking in Phase 3, matching in
Phase 4, survivorship in Phase 6.

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
