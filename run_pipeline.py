"""Run every pipeline stage end to end: raw data -> scorecard.

Phases 0-3: ingest, profile, the data-quality, standardization and age-review stages,
then the baseline matcher, blocking rules and evaluation. Ground-truth scoring
stays inside `src/evaluate.py`; its results are saved to reports/metrics.json.
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

from src import age_review, baseline, blocking, dq_rules, evaluate, ingest, matching_input, profile, standardize

DEFAULT_DB_PATH = ingest.DEFAULT_DB_PATH


def run_evaluation(db_path: Path | str) -> dict:
    """Score configured baseline and blocking tables and persist the results."""
    metrics = {
        "baseline.pairwise_metrics_by_variant": {
            variant_id: evaluate.pairwise_metrics(
                db_path, f"{baseline.TABLE_PREFIX}{variant_id}"
            )
            for variant_id, _ in baseline.load_variants()
        },
        "blocking.pair_completeness_by_rule": {
            rule_id: evaluate.pair_completeness(
                db_path, f"{blocking.TABLE_PREFIX}{rule_id}"
            )
            for rule_id, _ in blocking.load_rules()
        },
        "blocking.union_pair_completeness": evaluate.pair_completeness(
            db_path, blocking.UNION_TABLE
        ),
    }
    ingest.write_metrics(metrics)
    return metrics


# (stage name, callable taking a db path and returning a metrics dict)
STAGES = [
    ("ingest", ingest.run),
    ("profile", profile.run),
    ("dq_raw", dq_rules.run_raw),
    ("standardize", standardize.run),
    ("dq_std", partial(dq_rules.run_for, source_table=standardize.TABLE_NAME, stage="std")),
    ("age_review", age_review.run),
    ("matching_input", matching_input.run),
    ("baseline", partial(baseline.run, source_table=matching_input.TABLE_NAME)),
    ("blocking", partial(blocking.run, source_table=matching_input.TABLE_NAME)),
    ("evaluate", run_evaluation),
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
