# Phase 3 — worked examples for checking `evaluate.py`

**These are toy numbers.** The dataset below is invented for this note. It is not Febrl 3 and
nothing here is a pipeline result: no figure describes the real data. Every number was worked
by hand and re-checked with an independent script (not committed). Real results belong in
`reports/metrics.json`, once your `evaluate.py` produces them.

`src/evaluate.py` is yours to write. This note only gives you inputs and expected outputs to
check it against, and it makes no decision for you.

## Conventions these examples assume (confirm or change)

- A **true pair** is two records with the same `true_cluster_id`. Pairs are unordered.
- A pair table follows the contract in `src/pairs.py`: columns `unique_id_l`, `unique_id_r`,
  canonical (`l < r`), no self-pairs, no duplicates.
- Precision = TP / (TP + FP). Recall = TP / (TP + FN). F1 = 2TP / (2TP + FP + FN), which equals
  the harmonic mean of precision and recall whenever both are defined.
- Pair completeness = true pairs found in the table / all true pairs.
  Reduction ratio = 1 − rows / full pairs, with full pairs = n(n−1)/2.

## The toy dataset

| unique_id | true_cluster_id | | unique_id | true_cluster_id |
|---|---|---|---|---|
| 1 | 10 | | 5 | 20 |
| 2 | 10 | | 6 | 30 |
| 3 | 10 | | 7 | 30 |
| 4 | 20 | | 8 | 40 |

- n = 8, so **full pairs = 28**.
- Entity 10 has three records (3 pairs), entities 20 and 30 have two (1 pair each), entity 40 has
  one (0 pairs). **True pairs T = 5**: (1,2) (1,3) (2,3) (4,5) (6,7).

To load it in DuckDB:

```sql
CREATE TABLE raw_customers AS
SELECT * FROM (VALUES (1,10),(2,10),(3,10),(4,20),(5,20),(6,30),(7,30),(8,40))
       AS t(unique_id, true_cluster_id);
```

## `pairwise_metrics`: score a table of declared matches

| Case | Pair table | TP | FP | FN | Precision | Recall | F1 |
|---|---|---|---|---|---|---|---|
| A. Perfect | (1,2) (1,3) (2,3) (4,5) (6,7) | 5 | 0 | 0 | 1 | 1 | 1 |
| B. Mixed | (1,2) (1,3) (4,5) (1,4) | 3 | 1 | 2 | 3/4 = 0.75 | 3/5 = 0.6 | 2/3 ≈ 0.6667 |
| C. Chain | (1,2) (2,3) | 2 | 0 | 3 | 1 | 2/5 = 0.4 | 4/7 ≈ 0.5714 |
| D. Everything | all 28 pairs | 5 | 23 | 0 | 5/28 ≈ 0.1786 | 1 | 10/33 ≈ 0.3030 |
| E. Empty | (no rows) | 0 | 0 | 5 | 0/0, undefined | 0 | 0 |

- **B:** the false positive is (1,4), which joins entities 10 and 20. The false negatives are (2,3) and (6,7).
- **C:** records 1, 2, 3 are one entity, so a clustering step would infer (1,3) from (1,2) and (2,3).
  *Pairwise* scoring does not, so (1,3) counts as a miss. This is why Phase 5 has cluster-level metrics too.
- **E:** precision is 0/0. **What to return for an undefined value (None, NaN, 0.0, or raise) is your decision.**
  The same question arises for recall and completeness on a dataset with no true pairs.

## `pair_completeness`: how much of the truth survives blocking

| Case | Candidate table | Rows | True pairs inside | Completeness | Reduction ratio |
|---|---|---|---|---|---|
| F. A blocking rule | (1,2) (1,3) (2,3) (1,4) (2,4) (3,4) (4,5) | 7 | 4: (1,2) (1,3) (2,3) (4,5) | 4/5 = 0.8 | 1 − 7/28 = 0.75 |
| G. Full comparison | all 28 pairs | 28 | 5 | 1 | 0 |
| H. Empty | (no rows) | 0 | 0 | 0 | 1 |

- **F:** (6,7) is lost, and nothing downstream can recover it, which is why completeness is the ceiling on
  recall. Three of the seven candidates are not true pairs; completeness ignores them, because blocking is
  judged on what it keeps, not on how clean it is.
- **G:** comparing everything is always complete and saves nothing.

**The union** (what `blocking_pairs_union` is): rule A = (1,2) (4,5) (1,4) and rule B = (1,2) (6,7).

| Table | Rows | True pairs inside | Completeness | Reduction ratio |
|---|---|---|---|---|
| A | 3 | 2 | 2/5 = 0.4 | 1 − 3/28 ≈ 0.8929 |
| B | 2 | 2 | 2/5 = 0.4 | 1 − 2/28 ≈ 0.9286 |
| A ∪ B | 4 | 3 | 3/5 = 0.6 | 1 − 4/28 ≈ 0.8571 |

(1,2) is in both rules and counts once: the union has 4 rows, not 5.

## Checks to run on the real tables (no numbers quoted here)

1. **T is fixed.** `TP + FN` must be the same for every pair table you score. You can compute T
   independently from `ingest.cluster_size_distribution` in `reports/metrics.json`:
   T = Σ over sizes s of (number of clusters of size s) × s(s−1)/2. Compare it with `TP + FN`.
2. **Rows add up.** `TP + FP` must equal the table's row count, which `reports/metrics.json` also reports
   (`baseline.matched_pairs_by_variant`, `blocking.candidate_pairs_by_rule`, `blocking.union_candidate_pairs`).
3. **Subsets can't score higher.** If table P's rows are all inside table Q, then TP(P) ≤ TP(Q). The
   `surname_dob_postcode` baseline pairs are inside the `surname` blocking table, because they must agree on
   surname, so the baseline's TP cannot exceed the number of true pairs in that table.
4. **The union is at least as complete as each rule** and never above 1.
5. **Same arithmetic, different meaning.** Completeness of a candidate table is its recall, TP / T. A table
   scored as "predictions" and as "candidates" gives the same ratio. Only the interpretation differs: recall
   of a matcher versus the ceiling on recall for blocking.

## Not covered

Cluster-level metrics (Phase 5); unknown `unique_id`s in a pair table; non-canonical input such as (2,1) or
duplicate rows, which the pair-table contract rules out, so whether `evaluate.py` re-checks it is up to you.
