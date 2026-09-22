"""Run every pipeline stage end to end: raw data -> scorecard.

Phase 0 skeleton. Only the ingest stage exists so far; later phases append to
`STAGES` in order. The guard test `tests/test_raw_untouched.py` runs this module,
so it must stay runnable against an arbitrary DuckDB path.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from src import ingest

DEFAULT_DB_PATH = ingest.DEFAULT_DB_PATH

# (stage name, callable taking a db path and returning a metrics dict)
STAGES = [
    ("ingest", ingest.run),
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
