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