"""Run every pipeline stage end to end: raw data -> scorecard.

Phases 0-3: ingest, profile, the data-quality, standardization and age-review stages,
then the baseline matcher and the blocking rules. Scoring them against ground truth is
`src/evaluate.py`, which the owner writes and which is not wired in until it exists.
Later phases append to `STAGES` in order. The guard test
`tests/test_raw_untouched.py` runs this module, so it must stay runnable against
an arbitrary DuckDB path.

The DQ rules are evaluated twice, before and after standardization, which is what
Phase 2 asks to be reported. Each pass writes its own table, so neither the
before nor the after counts can be overwritten by the other.
"""

from __future__ import annotations

import argparse
from functools import partial
from pathlib import Path

from src import age_review, baseline, blocking, dq_rules, ingest, profile, standardize

DEFAULT_DB_PATH = ingest.DEFAULT_DB_PATH

# (stage name, callable taking a db path and returning a metrics dict)
STAGES = [
    ("ingest", ingest.run),
    ("profile", profile.run),
    ("dq_raw", dq_rules.run_raw),
    ("standardize", standardize.run),
    ("dq_std", partial(dq_rules.run_for, source_table=standardize.TABLE_NAME, stage="std")),
    ("age_review", age_review.run),
    ("baseline", baseline.run),
    ("blocking", blocking.run),
]


def run(db_path: Path | str = DEFAULT_DB_PATH) -> dict:
    """Run every stage in order and return the merged metrics."""
    metrics: dict = {}
    for name, stage in STAGES:
        print(f"[{name}] running")
        metrics.update(stage(db_path) or {})
    return metrics


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default=str(DEFAULT_DB_PATH), help="path to the DuckDB file")
    args = parser.parse_args()

    for key, value in run(args.db).items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
