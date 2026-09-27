# Phase 0–1 code: questions and answers

Worked through on 2026-09-27 to move from "what each file is for" to "how the code
actually behaves". Try re-answering each question before reading the answer.

---

## Q1 — What range can `last_updated` take? Is 22 Sep 2026 possible?

```python
start = LAST_UPDATED_REFERENCE_DATE - timedelta(days=LAST_UPDATED_WINDOW_DAYS - 1)
start + timedelta(days=stable_hash("last_updated", rec_id, seed) % LAST_UPDATED_WINDOW_DAYS)
```

**Answer:** 24 Sep 2023 to 22 Sep 2026, both inclusive. Yes, 22 Sep 2026 is possible.

- `hash % 1095` gives 0 to 1094 (1,095 possible values).
- `start` = 22 Sep 2026 − 1094 days = 24 Sep 2023.
- `start + 0` is the earliest date; `start + 1094` = 22 Sep 2026 is the latest.
- The `- 1` keeps the end date inside the window. Stepping back the full 1095 days
  would shift the window one day early: 23 Sep 2023 would appear and 22 Sep 2026
  never could. That is an **off-by-one error**.

**Key idea:** `x % n` always lands in 0 to n−1, however large `x` is.
(7-day example: step back 6 days from Sunday 7th to Monday 1st, add 0–6 → Monday to Sunday.)

---

## Q2 — What changes if `RANDOM_SEED` goes from 42 to 7?

The seed only appears in the string that is hashed: `f"{seed}:{namespace}:{key}"`.

**Answer:**

| Thing | Changes? | Why |
|---|---|---|
| `source_system` | Yes, but ~⅓ of records keep their value by chance | `% 3` has only 3 outcomes |
| `last_updated` | Yes; ~1 in 1,095 records keep their value by chance | `% 1095` |
| `unique_id` | Yes, whole order reshuffles | hash-ordered |
| Febrl fields, `true_cluster_id` | No | never pass through the hash |
| Any test | All still pass | each test's runs use the same seed; hashing is deterministic |
| `data/raw/febrl3.csv` | No | (1) function returns early if the file exists; (2) it only holds `rec_id` + Febrl columns, sorted by `rec_id` |

**Key ideas**
- SHA-256 is not random: the same input always gives the same output. Its outputs
  only *look* random. "Chance" only appears when comparing two *different* inputs.
- How likely a coincidence is depends on the number of outcomes after `%`, not on
  how different the hashes are.
- The reproducibility tests prove **consistency**, not **correctness**: a bug is
  reproduced identically on every run. `tests/test_ingest_invariants.py` checks
  properties instead (dates inside the window, exactly three systems, `unique_id`
  a permutation, ground truth seed-independent) for seeds 42 and 7. Removing the
  `- 1` makes it fail; the old suite would not have noticed.

---

## Q3 — Leak ground truth past `test_no_label_leakage.py`

The guard fails if the *text* `true_cluster_id` or `rec_id` appears on a line of a `src/` file.

**Answer:** it checks the characters in the file, not the data the code uses. Two ways past it:

```python
df = con.execute("SELECT * FROM raw_customers").fetch_df()   # * returns every column
col = "true_" + "cluster_id"                                  # name built at runtime
labels = df[col]
```

**Key ideas**
- A text search catches accidents, not hidden or deliberate leaks. The rule in
  `AGENTS.md` and your review are the real protection.
- A stronger guard checks the data at the boundary (Phase 4, `model.py`):

  ```python
  FORBIDDEN = {"true_" + "cluster_id", "rec" + "_id"}
  assert FORBIDDEN.isdisjoint(df.columns), "ground truth reached the matcher"
  ```

---

## Q4 — What does `profile_column` do with a column that is entirely NULL?

**Answer:**

| Stat | Result |
|---|---|
| `total_rows`, `null_count` | 5000, 5000 (null rate 100%) |
| `distinct_count` | 0 — `COUNT(DISTINCT …)` ignores NULLs |
| `min_length`, `max_length` | SQL `NULL` → Python `None` |
| Report row | `\| Min length \| None \|` |
| Top values / patterns | `*(no non-null values)*`, 0 patterns |

Without `None if min_length is None else int(min_length)`, `int(None)` raises a
`TypeError` and the profiling stage crashes.

**Key idea:** over zero rows, `COUNT` returns **0**, but `MIN`, `MAX`, `SUM`, `AVG`
return **NULL**. 0 would also be the wrong meaning: a minimum length of 0 would claim
an empty string exists.

Check it yourself (predict first, then run):

```sql
SELECT COUNT(*), MIN(x) FROM (SELECT NULL AS x) WHERE x IS NOT NULL;
```

---

## Q5 — Do `rec-12-org` and `rec-12-dup-0` get close `unique_id`s?

**Answer:** nothing can be said about how close they are, and that is the intended result.

- Each record's position comes from hashing a different string
  (`"42:unique_id:rec-12-org"` vs `"42:unique_id:rec-12-dup-0"`); the hashes are unrelated.
- The two IDs behave like independent random positions among 5,000: roughly a 0.4%
  chance of landing within 10 of each other.
- If they were reliably close, the ID would leak which records belong together.
  That is why `assign_unique_id` does not number rows in `rec_id` order.

**Key idea:** the absence of any pattern is exactly what stops `unique_id` leaking the answer key.

---

## Habits that came out of this

1. **Predict before you run.** Write down the expected row count, min/max, or which tests pass; then check.
2. **Use a tiny example** (3 rows, a 7-day window, `% 3`) before reasoning about the real numbers.
3. **Break it on purpose.** Remove the `- 1`, change `% 3` to `% 2`, and see what the tests and the profile catch.
