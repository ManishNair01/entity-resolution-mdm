"""Phase 3 — scoring against ground truth. STUBS ONLY: the owner writes this file.

`AGENTS.md` hard rule 6 and roadmap section 10.1 make `evaluate.py` owner-written.
This module is the only one, besides `ingest.py`, allowed to reference ground truth
(`true_cluster_id` and `rec_id`, both held in `raw_customers`); everything else works
from the opaque `unique_id`. The signatures below only fix what the agent-written
`baseline.py` and `blocking.py` hand over, so the owner can fill in the bodies.

The contract for a pair table, the same one `src/pairs.py` writes: exactly the
columns `unique_id_l` and `unique_id_r`, one row per canonical unordered pair
(`unique_id_l < unique_id_r`), no self-pairs, no duplicates. The tables the
pipeline produces are `baseline_pairs_<variant id>`, `blocking_pairs_<rule id>` and
`blocking_pairs_union`.

Anything this module computes belongs in `reports/metrics.json` (architecture rule
3). Until these bodies exist it is not wired into `run_pipeline.py`, so no precision,
recall, F1 or pair-completeness number exists yet and none may be written anywhere.
"""

from __future__ import annotations

from pathlib import Path


def pairwise_metrics(db_path: Path | str, pairs_table: str) -> dict:
    """Score a table of declared-match pairs against ground truth.

    Inputs: the DuckDB file and the name of a pair table (contract above).
    Output: a dict with the pairwise true positives, false positives, false negatives,
    precision, recall and F1 of `pairs_table`, where a true pair is any two records
    that share a ground-truth entity.
    Intent: measure the baseline, and later the probabilistic model, with one
    function, so the two are scored on exactly the same footing.
    """
    raise NotImplementedError("owner-written: see the module docstring")


def pair_completeness(db_path: Path | str, pairs_table: str) -> float:
    """Share of true duplicate pairs that appear in a candidate pair table.

    Inputs: the DuckDB file and the name of a pair table (contract above).
    Output: a number in [0, 1]: true pairs present in `pairs_table` divided by all
    true pairs.
    Intent: blocking can only lose true matches, never add them, so this is the
    ceiling on any later recall. It is the number blocking is chosen on.
    """
    raise NotImplementedError("owner-written: see the module docstring")
