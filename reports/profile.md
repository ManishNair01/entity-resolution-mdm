# Data Profile — raw_customers

All numbers below come from `reports/metrics.json`, written by `src/ingest.py` and `src/profile.py` (AGENTS.md architecture rule 3).

## Duplicate rate and cluster sizes

| Metric | Value |
|---|---|
| Records | 5000 |
| True entities | 2000 |
| Duplicate records | 3000 |
| Duplicate rate (duplicate records / records) | 60.00% |
| Records per entity (records / entities) | 2.500 |
| Cluster size, min | 1 |
| Cluster size, max | 6 |

**Cluster-size distribution**

| Cluster size | Number of clusters |
|---|---|
| 1 | 835 |
| 2 | 368 |
| 3 | 256 |
| 4 | 212 |
| 5 | 161 |
| 6 | 168 |

## Column profiles

### `given_name`

**Completeness**

| Metric | Value |
|---|---|
| Rows | 5000 |
| Null count | 156 |
| Null rate | 3.12% |
| Empty-string count | 0 |
| Empty-string rate | 0.00% |
| Distinct count | 1213 |
| Min length | 2 |
| Max length | 12 |

**Top 10 values**

| Value | Count |
|---|---|
| joshua | 81 |
| emiily | 69 |
| jack | 61 |
| benjamin | 54 |
| isabella | 51 |
| samuel | 49 |
| thomas | 47 |
| sophie | 46 |
| james | 45 |
| william | 42 |

**Format patterns** (digits -> `9`, letters -> `A`)

35 distinct pattern(s). Top 10 by count:

| Pattern | Count |
|---|---|
| AAAAAA | 1257 |
| AAAAA | 1096 |
| AAAAAAA | 849 |
| AAAA | 713 |
| AAAAAAAA | 473 |
| AAAAAAAAA | 209 |
| AAA | 150 |
| AAAAAAAAAA | 18 |
| AAAAAAAAAAA | 13 |
| AAAA-AAAA | 5 |

### `surname`

**Completeness**

| Metric | Value |
|---|---|
| Rows | 5000 |
| Null count | 79 |
| Null rate | 1.58% |
| Empty-string count | 0 |
| Empty-string rate | 0.00% |
| Distinct count | 1740 |
| Min length | 2 |
| Max length | 18 |

**Top 10 values**

| Value | Count |
|---|---|
| white | 123 |
| clarke | 86 |
| campbell | 73 |
| ryan | 69 |
| green | 57 |
| reid | 50 |
| dixon | 47 |
| nguyen | 46 |
| matthews | 44 |
| morrison | 44 |

**Format patterns** (digits -> `9`, letters -> `A`)

52 distinct pattern(s). Top 10 by count:

| Pattern | Count |
|---|---|
| AAAAAA | 1111 |
| AAAAA | 963 |
| AAAAAAA | 879 |
| AAAAAAAA | 771 |
| AAAA | 476 |
| AAAAAAAAA | 285 |
| AAAAAAAAAA | 162 |
| AAAAAAAAAAA | 91 |
| AAA | 47 |
| AAAAAAAAAAAA | 28 |

### `street_number`

**Completeness**

| Metric | Value |
|---|---|
| Rows | 5000 |
| Null count | 245 |
| Null rate | 4.90% |
| Empty-string count | 0 |
| Empty-string rate | 0.00% |
| Distinct count | 342 |
| Min length | 1 |
| Max length | 4 |

**Top 10 values**

| Value | Count |
|---|---|
| 1 | 166 |
| 3 | 159 |
| 5 | 150 |
| 8 | 134 |
| 4 | 132 |
| 16 | 119 |
| 7 | 117 |
| 11 | 111 |
| 12 | 110 |
| 6 | 107 |

**Format patterns** (digits -> `9`, letters -> `A`)

4 distinct pattern(s). Top 10 by count:

| Pattern | Count |
|---|---|
| 99 | 2946 |
| 9 | 1135 |
| 999 | 640 |
| 9999 | 34 |

### `address_1`

**Completeness**

| Metric | Value |
|---|---|
| Rows | 5000 |
| Null count | 154 |
| Null rate | 3.08% |
| Empty-string count | 0 |
| Empty-string rate | 0.00% |
| Distinct count | 2358 |
| Min length | 5 |
| Max length | 30 |

**Top 10 values**

| Value | Count |
|---|---|
| newman morris circuit | 18 |
| ashburton circuit | 17 |
| endeavour street | 16 |
| oxley street | 16 |
| hilder street | 13 |
| kitchener street | 13 |
| leahy close | 13 |
| sinclair street | 13 |
| tenison-woods circuit | 13 |
| macfarland crescent | 12 |

**Format patterns** (digits -> `9`, letters -> `A`)

239 distinct pattern(s). Top 10 by count:

| Pattern | Count |
|---|---|
| AAAAAAA AAAAAA | 434 |
| AAAAAA AAAAAA | 340 |
| AAAAAAAAA AAAAAA | 299 |
| AAAAAA AAAAA | 262 |
| AAAAAAAA AAAAAA | 259 |
| AAAAAAA AAAAA | 255 |
| AAAAA AAAAAA | 250 |
| AAAAA AAAAA | 175 |
| AAAAAAA AAAAAAAA | 171 |
| AAAAAAAA AAAAAAAA | 149 |

### `address_2`

**Completeness**

| Metric | Value |
|---|---|
| Rows | 5000 |
| Null count | 693 |
| Null rate | 13.86% |
| Empty-string count | 0 |
| Empty-string rate | 0.00% |
| Distinct count | 2303 |
| Min length | 3 |
| Max length | 41 |

**Top 10 values**

| Value | Count |
|---|---|
| brentwood vlge | 32 |
| rowethorpe | 28 |
| villa 2 | 21 |
| john flynn medical centre | 18 |
| rosedale | 18 |
| st francis vlge | 16 |
| mlc centre | 13 |
| glenlee | 12 |
| killarney | 12 |
| rosetta village | 12 |

**Format patterns** (digits -> `9`, letters -> `A`)

454 distinct pattern(s). Top 10 by count:

| Pattern | Count |
|---|---|
| AAAAAAAAA | 381 |
| AAAAAAAA | 371 |
| AAAAAAA | 356 |
| AAAAAAAAAA | 199 |
| AAAAAA | 189 |
| AAAAA AAAAA | 87 |
| AAAAAAA AAAA | 84 |
| AAAAAAA AAAAA | 81 |
| AAAAA | 80 |
| AAAAAA AAAA | 79 |

### `suburb`

**Completeness**

| Metric | Value |
|---|---|
| Rows | 5000 |
| Null count | 85 |
| Null rate | 1.70% |
| Empty-string count | 0 |
| Empty-string rate | 0.00% |
| Distinct count | 1706 |
| Min length | 3 |
| Max length | 21 |

**Top 10 values**

| Value | Count |
|---|---|
| frankston | 44 |
| mosman | 33 |
| toowoomba | 29 |
| coffs harbour | 23 |
| dianella | 21 |
| orange | 19 |
| balwyn north | 18 |
| belmont | 18 |
| sunshine | 18 |
| auburn | 17 |

**Format patterns** (digits -> `9`, letters -> `A`)

117 distinct pattern(s). Top 10 by count:

| Pattern | Count |
|---|---|
| AAAAAAAA | 735 |
| AAAAAAA | 661 |
| AAAAAAAAA | 622 |
| AAAAAA | 410 |
| AAAAAAAAAA | 353 |
| AAAAA | 207 |
| AAAAAAAAAAA | 205 |
| AAAAA AAAAA | 122 |
| AAAAAA AAAAA | 87 |
| AAAAAA AAAA | 86 |

### `postcode`

**Completeness**

| Metric | Value |
|---|---|
| Rows | 5000 |
| Null count | 0 |
| Null rate | 0.00% |
| Empty-string count | 0 |
| Empty-string rate | 0.00% |
| Distinct count | 1273 |
| Min length | 4 |
| Max length | 4 |

**Top 10 values**

| Value | Count |
|---|---|
| 2250 | 30 |
| 6210 | 29 |
| 2570 | 26 |
| 2756 | 23 |
| 4740 | 22 |
| 2170 | 21 |
| 2830 | 21 |
| 4670 | 20 |
| 2280 | 19 |
| 3128 | 18 |

**Format patterns** (digits -> `9`, letters -> `A`)

1 distinct pattern(s). Top 10 by count:

| Pattern | Count |
|---|---|
| 9999 | 5000 |

### `state`

**Completeness**

| Metric | Value |
|---|---|
| Rows | 5000 |
| Null count | 85 |
| Null rate | 1.70% |
| Empty-string count | 0 |
| Empty-string rate | 0.00% |
| Distinct count | 35 |
| Min length | 2 |
| Max length | 3 |

**Top 10 values**

| Value | Count |
|---|---|
| nsw | 1581 |
| vic | 1212 |
| qld | 821 |
| wa | 496 |
| sa | 463 |
| tas | 118 |
| act | 96 |
| nt | 57 |
| nws | 13 |
| vci | 11 |

**Format patterns** (digits -> `9`, letters -> `A`)

2 distinct pattern(s). Top 10 by count:

| Pattern | Count |
|---|---|
| AAA | 3888 |
| AA | 1027 |

### `date_of_birth`

**Completeness**

| Metric | Value |
|---|---|
| Rows | 5000 |
| Null count | 155 |
| Null rate | 3.10% |
| Empty-string count | 0 |
| Empty-string rate | 0.00% |
| Distinct count | 2089 |
| Min length | 8 |
| Max length | 8 |

**Top 10 values**

| Value | Count |
|---|---|
| 19070923 | 12 |
| 19811017 | 10 |
| 19940729 | 9 |
| 19960904 | 9 |
| 19010927 | 8 |
| 19020831 | 7 |
| 19100830 | 7 |
| 19110405 | 7 |
| 19260419 | 7 |
| 19471027 | 7 |

**Format patterns** (digits -> `9`, letters -> `A`)

1 distinct pattern(s). Top 10 by count:

| Pattern | Count |
|---|---|
| 99999999 | 4845 |

### `soc_sec_id`

**Completeness**

| Metric | Value |
|---|---|
| Rows | 5000 |
| Null count | 0 |
| Null rate | 0.00% |
| Empty-string count | 0 |
| Empty-string rate | 0.00% |
| Distinct count | 2291 |
| Min length | 7 |
| Max length | 7 |

**Top 10 values**

| Value | Count |
|---|---|
| 1042252 | 6 |
| 1045315 | 6 |
| 1327917 | 6 |
| 1390881 | 6 |
| 1421166 | 6 |
| 1515266 | 6 |
| 1646449 | 6 |
| 1677968 | 6 |
| 1690126 | 6 |
| 2122377 | 6 |

**Format patterns** (digits -> `9`, letters -> `A`)

1 distinct pattern(s). Top 10 by count:

| Pattern | Count |
|---|---|
| 9999999 | 5000 |

### `source_system`

**Completeness**

| Metric | Value |
|---|---|
| Rows | 5000 |
| Null count | 0 |
| Null rate | 0.00% |
| Empty-string count | 0 |
| Empty-string rate | 0.00% |
| Distinct count | 3 |
| Min length | 3 |
| Max length | 8 |

**Top 10 values**

| Value | Count |
|---|---|
| ERP | 1697 |
| CRM | 1663 |
| WEB_FORM | 1640 |

**Format patterns** (digits -> `9`, letters -> `A`)

2 distinct pattern(s). Top 10 by count:

| Pattern | Count |
|---|---|
| AAA | 3360 |
| AAA_AAAA | 1640 |

### `last_updated`

**Completeness**

| Metric | Value |
|---|---|
| Rows | 5000 |
| Null count | 0 |
| Null rate | 0.00% |
| Empty-string count | 0 |
| Empty-string rate | 0.00% |
| Distinct count | 1079 |
| Min length | 10 |
| Max length | 10 |

**Top 10 values**

| Value | Count |
|---|---|
| 2025-11-03 | 14 |
| 2025-03-08 | 12 |
| 2025-04-27 | 12 |
| 2025-07-06 | 12 |
| 2025-01-24 | 11 |
| 2025-10-23 | 11 |
| 2026-08-03 | 11 |
| 2023-10-12 | 10 |
| 2024-02-28 | 10 |
| 2024-03-02 | 10 |

**Format patterns** (digits -> `9`, letters -> `A`)

1 distinct pattern(s). Top 10 by count:

| Pattern | Count |
|---|---|
| 9999-99-99 | 5000 |

<!-- Embedded from reports/problems_observed.md (owner-written). Edit that file, not this section: profile.md is regenerated on every run. -->

## Problems observed

**P1 — `date_of_birth`: impossible calendar dates.** All values match the 8-digit
`YYYYMMDD` pattern, but 35 records (0.7%) aren't real dates. Examples: `19320239`
(Feb 39), `19875031` (month 50). Each appears once, which is consistent with keying
errors.
→ **Phase 2:** a validity rule that flags values that don't parse as dates. Flag
them rather than fixing them, because the true date can't be recovered.

**P2 — `state`: invalid state codes.** 35 distinct values against 8 valid codes
(`nsw`, `vic`, `qld`, `sa`, `wa`, `tas`, `nt`, `act`; reference: ISO 3166-2:AU).
27 invalid codes across 71 records (1.42%); a further 85 records are NULL (see P3).
The invalid codes fall into two kinds of error:
- *Letters swapped:* `nws` → `nsw` (13 records), `vci` → `vic` (11).
- *One wrong letter, often a neighbouring key on the keyboard:* `nsq` → `nsw` (5), `qls` → `qld` (4).

Some codes can't be corrected with certainty: `as` could be `sa` (letters swapped)
or `wa` (one letter wrong).
→ **Phase 2:** a validity rule against the ISO 3166-2:AU list. Open decision on
correction: auto-correct only when one valid code is closest and flag the rest, or
derive the state from the postcode (unreliable where the postcode itself is wrong, see P4).

**P3 — identity fields: missing values.** Nulls in fields needed to identify a person:

| Field | Missing | % of records |
|---|---|---|
| `given_name` | 156 | 3.12% |
| `surname` | 79 | 1.58% |
| `date_of_birth` | 155 | 3.10% |
| `state` | 85 | 1.70% |

6 records have neither a given name nor a surname. Examples: `rec-1707-org`
(no given name), `rec-1166-org` (no date of birth), `rec-1925-dup-1` (no surname).
Missing values occur in original records as well as duplicates, so the original
can't be treated as a complete reference.
→ **Phase 2:** completeness rules; decide which fields are mandatory for a usable
customer record, and whether records with no name at all are kept, flagged or excluded.

**P4 — `postcode`: disagrees between duplicates.** 410 of 1,165 people with
duplicates (35.2%) have more than one postcode across their records. Mostly
swapped digits: `rec-6-org` `2621` vs `rec-6-dup-2` `2612`; `rec-7-org` `2161`
vs `rec-7-dup-2` `2116`. Every value is a valid 4-digit postcode, so no validity
rule can detect this.
→ **Phase 4:** postcode needs a fuzzy comparison level (e.g. one edit apart), not
exact match only.

**P5 — `soc_sec_id`: disagrees between duplicates.** 254 of 1,165 people with
duplicates (21.8%). Two kinds: swapped digits (`rec-6-org` `3871937` vs
`rec-6-dup-1` `3871397`; `rec-12-org` `5752610` vs `rec-12-dup-0` `5752601`), and
completely different values (`rec-6-dup-3` `8329801`; `rec-12-dup-4` `4216940`).
→ **Phase 4:** the ID can't be used as an exact-match key or a sole blocking key;
use a fuzzy level, and rely on other fields when the value has been replaced.

**P6 — `date_of_birth`: disagrees between duplicates.** 173 of 1,165 people with
duplicates (14.8%). One digit changed: `rec-14-org` `19021119` vs `rec-14-dup-0`
`19021219`. Completely different: `rec-25-org` `19601231` vs `rec-25-dup-2`
`19600804`. Separate from P1: these are valid dates, just wrong.
→ **Phase 4:** a date comparison that tolerates small differences.

**P7 — `given_name` / `surname`: names swapped between fields.** At least 125 of
1,165 people with duplicates (10.7%) have a record with given name and surname
swapped. Examples: `rec-582-dup-1` `lauren crea` vs `rec-582-dup-2` `crea lauren`;
`rec-12-org` `barnaby siggins` vs `rec-12-dup-4` `siggins barnaby`.
→ **Phase 4:** compare names across fields as well as within them, so a swapped
record still scores as a match.

**P8 — `given_name` / `surname`: misspellings and replaced surnames.** Typos:
`gillard` → `gillatd`, `gillaird`; `goldsworthy` → `goldsworpthy`; `barnaby` →
`barnayb`, `barnabh`; inserted space: `braiden` → `braid en`. Replaced surnames:
`rec-6-dup-0` `dunnicliff` (original `gillard`), `rec-7-dup-2` `caruana` (original
`goldsworthy`).
→ **Phase 2:** standardization can trim spaces but must not "correct" spellings.
**Phase 4:** fuzzy name comparison (e.g. Jaro-Winkler); replaced surnames must be
outweighed by agreement on other fields.
