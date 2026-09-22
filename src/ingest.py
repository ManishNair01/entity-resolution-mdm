"""Phase 0 — load Febrl 3, attach ground truth and synthetic metadata, write `raw_customers`.

This is the only module besides `evaluate.py` allowed to reference `true_cluster_id`
(AGENTS.md, hard rule 1). Everything downstream must treat the label as absent.

Record-ID format confirmed against the installed dataset (recordlinkage 0.16):
    rec-<N>-org       2000 rows
    rec-<N>-dup-<k>   3000 rows
`<N>` is the true entity, so it becomes `true_cluster_id`.
"""

from __future__ import annotations

import argparse
import json
import random
import re
from datetime import date, timedelta
from pathlib import Path

import duckdb
import pandas as pd
from recordlinkage.datasets import load_febrl3

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB_PATH = PROJECT_ROOT / "data" / "mdm.duckdb"
RAW_SNAPSHOT_PATH = PROJECT_ROOT / "data" / "raw" / "febrl3.csv"
METRICS_PATH = PROJECT_ROOT / "reports" / "metrics.json"

TABLE_NAME = "raw_customers"

# --- Determinism (AGENTS.md architecture rule 4) ------------------------------
# One seed drives the row shuffle and both synthetic columns, so two runs produce
# byte-identical tables.
RANDOM_SEED = 42

# --- Synthetic metadata (roadmap section 2) -----------------------------------
# Febrl has no source system or timestamp; both columns below are invented so that
# survivorship rules in Phase 6 have something to work with. Documented as synthetic
# in the README (Phase 7). `last_updated` is drawn from a window ending on a fixed
# reference date rather than "today", otherwise the table would change every day.
SOURCE_SYSTEMS = ("CRM", "ERP", "WEB_FORM")
LAST_UPDATED_REFERENCE_DATE = date(2026, 9, 22)
LAST_UPDATED_WINDOW_DAYS = 3 * 365

FEBRL_COLUMNS = [
    "given_name",
    "surname",
    "street_number",
    "address_1",
    "address_2",
    "suburb",
    "postcode",
    "state",
    "date_of_birth",
    "soc_sec_id",
]

REC_ID_PATTERN = re.compile(r"^rec-(?P<cluster>\d+)-(?:org|dup-\d+)$")


def load_source_frame() -> pd.DataFrame:
    """Load Febrl 3 as a flat frame with `rec_id` as a column, not an index.

    Returns a frame of 5,000 rows: the 10 Febrl fields plus `rec_id`, all as
    strings, exactly as the package ships them. No cleaning happens here.
    """
    frame = load_febrl3().reset_index()
    if frame.index.size != len(frame):  # pragma: no cover - defensive
        raise AssertionError("unexpected index after reset_index")
    return frame[["rec_id"] + FEBRL_COLUMNS]


def derive_true_cluster_id(rec_ids: pd.Series) -> pd.Series:
    """Extract the true entity number from each record ID.

    `rec-123-org` and `rec-123-dup-0` both belong to entity 123. Raises if any ID
    does not match the expected format, so a dataset change fails loudly instead
    of silently producing wrong ground truth.
    """
    extracted = rec_ids.str.extract(REC_ID_PATTERN, expand=False)
    unmatched = rec_ids[extracted.isna()]
    if not unmatched.empty:
        raise ValueError(
            f"{len(unmatched)} record IDs do not match {REC_ID_PATTERN.pattern!r}, "
            f"e.g. {unmatched.iloc[0]!r}"
        )
    return extracted.astype("int64")


def add_synthetic_metadata(frame: pd.DataFrame, seed: int = RANDOM_SEED) -> pd.DataFrame:
    """Attach the invented `source_system` and `last_updated` columns.

    Both are drawn uniformly from a seeded generator: `source_system` over
    CRM / ERP / WEB_FORM, `last_updated` over the `LAST_UPDATED_WINDOW_DAYS` days
    ending on `LAST_UPDATED_REFERENCE_DATE`.
    """
    rng = random.Random(seed)
    out = frame.copy()
    start = LAST_UPDATED_REFERENCE_DATE - timedelta(days=LAST_UPDATED_WINDOW_DAYS - 1)
    out["source_system"] = [rng.choice(SOURCE_SYSTEMS) for _ in range(len(out))]
    out["last_updated"] = [
        start + timedelta(days=rng.randrange(LAST_UPDATED_WINDOW_DAYS)) for _ in range(len(out))
    ]
    return out


def assign_unique_id(frame: pd.DataFrame, seed: int = RANDOM_SEED) -> pd.DataFrame:
    """Shuffle deterministically, then number the rows 0..n-1 as `unique_id`.

    Splink needs an integer key. The shuffle matters: if IDs were handed out in
    `rec_id` order, records of one entity would get adjacent IDs and the key would
    itself carry ground truth.
    """
    rng = random.Random(seed)
    order = list(range(len(frame)))
    rng.shuffle(order)
    out = frame.iloc[order].reset_index(drop=True)
    out.insert(0, "unique_id", pd.Series(range(len(out)), dtype="int64"))
    return out


def build_raw_customers(seed: int = RANDOM_SEED) -> pd.DataFrame:
    """Build the full `raw_customers` frame in memory."""
    frame = load_source_frame()
    frame["true_cluster_id"] = derive_true_cluster_id(frame["rec_id"])
    frame = add_synthetic_metadata(frame, seed=seed)
    return assign_unique_id(frame, seed=seed)


def write_raw_snapshot(frame: pd.DataFrame, path: Path | None = None) -> None:
    """Keep an untouched CSV copy of the source fields under `data/raw/`.

    Written once; if the file already exists it is left alone, since `data/raw/`
    is meant to be the immutable source snapshot.
    """
    path = Path(path) if path is not None else RAW_SNAPSHOT_PATH
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.sort_values("rec_id")[["rec_id"] + FEBRL_COLUMNS].to_csv(path, index=False)


def write_metrics(metrics: dict, path: Path | None = None) -> None:
    """Merge `metrics` into `reports/metrics.json`, the single source of numbers.

    Reports and the README may quote these values and nothing else
    (AGENTS.md architecture rule 3).
    """
    path = Path(path) if path is not None else METRICS_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    existing.update(metrics)
    path.write_text(json.dumps(existing, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run(db_path: Path | str = DEFAULT_DB_PATH, seed: int = RANDOM_SEED) -> dict:
    """Write the `raw_customers` table and return this stage's metrics.

    `raw_customers` is rebuilt from the source package rather than edited, so the
    rule that no stage modifies it still holds: the same seed reproduces the same
    rows, and no later stage writes to this table.
    """
    frame = build_raw_customers(seed=seed)
    write_raw_snapshot(frame)

    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    columns = ", ".join(
        ["unique_id", "rec_id", *FEBRL_COLUMNS, "source_system"]
        + ["CAST(last_updated AS DATE) AS last_updated", "true_cluster_id"]
    )
    with duckdb.connect(str(db_path)) as con:
        con.register("raw_frame", frame)
        con.execute(
            f"CREATE OR REPLACE TABLE {TABLE_NAME} AS "
            f"SELECT {columns} FROM raw_frame ORDER BY unique_id"
        )
        con.unregister("raw_frame")

    metrics = {
        "ingest.record_count": int(len(frame)),
        "ingest.true_entity_count": int(frame["true_cluster_id"].nunique()),
        "ingest.original_record_count": int(frame["rec_id"].str.endswith("-org").sum()),
        "ingest.duplicate_record_count": int(frame["rec_id"].str.contains("-dup-").sum()),
    }
    write_metrics(metrics)
    return metrics


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default=str(DEFAULT_DB_PATH), help="path to the DuckDB file")
    parser.add_argument("--seed", type=int, default=RANDOM_SEED)
    args = parser.parse_args()

    metrics = run(args.db, seed=args.seed)
    for key, value in metrics.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
