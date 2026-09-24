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
import hashlib
import json
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

# An aggregate of the ground truth: one row per cluster size, holding how many
# entities have that many records. Phase 1 needs the duplicate rate and the cluster
# size distribution, but hard rule 1 keeps the label inside this module, so the
# label is collapsed to counts here. No row in this table can be traced back to an
# entity, which is what makes it safe for a later stage to read.
GROUND_TRUTH_TABLE = "ground_truth_cluster_sizes"

# --- Determinism (AGENTS.md architecture rule 4) ------------------------------
# Everything random here is derived from SHA-256 of the record's own ID plus this
# seed, not from a random number generator. A generator would make the output
# depend on the order rows arrive in and on the RNG's stream staying stable across
# Python versions; CPython only guarantees that for `random.random()`. Hashing the
# key makes each row's values a pure function of that row, so a fresh clone on a
# different Python or platform rebuilds a byte-identical table.
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


def stable_hash(namespace: str, key: str, seed: int = RANDOM_SEED) -> int:
    """Return a stable 64-bit integer for `key` within `namespace`.

    The namespace keeps the three derived values independent: a record's source
    system tells you nothing about its timestamp or its position. Unlike
    `hash()`, SHA-256 is identical across processes, Python versions and
    platforms, which is what makes the fresh-clone test reproducible.
    """
    digest = hashlib.sha256(f"{seed}:{namespace}:{key}".encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big")


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

    Each row's values come from a hash of its own `rec_id`: `source_system` over
    CRM / ERP / WEB_FORM, `last_updated` over the `LAST_UPDATED_WINDOW_DAYS` days
    ending on `LAST_UPDATED_REFERENCE_DATE`. The spread is near-uniform, and the
    modulo bias is negligible at 64 bits against these ranges.
    """
    out = frame.copy()
    start = LAST_UPDATED_REFERENCE_DATE - timedelta(days=LAST_UPDATED_WINDOW_DAYS - 1)
    out["source_system"] = [
        SOURCE_SYSTEMS[stable_hash("source_system", rec_id, seed) % len(SOURCE_SYSTEMS)]
        for rec_id in out["rec_id"]
    ]
    out["last_updated"] = [
        start + timedelta(days=stable_hash("last_updated", rec_id, seed) % LAST_UPDATED_WINDOW_DAYS)
        for rec_id in out["rec_id"]
    ]
    return out


def assign_unique_id(frame: pd.DataFrame, seed: int = RANDOM_SEED) -> pd.DataFrame:
    """Order rows by a hash of `rec_id`, then number them 0..n-1 as `unique_id`.

    Splink needs an integer key. The hash ordering matters twice over: if IDs were
    handed out in `rec_id` order, records of one entity would get adjacent IDs and
    the key would itself carry ground truth; and ordering by hash rather than by
    arrival position means the IDs do not depend on the order `recordlinkage` hands
    the rows back. `rec_id` breaks ties, so the ordering is total even if two
    hashes collide.
    """
    out = frame.copy()
    order_key = [(stable_hash("unique_id", rec_id, seed), rec_id) for rec_id in out["rec_id"]]
    out["_order_key"] = order_key
    out = out.sort_values("_order_key").drop(columns="_order_key").reset_index(drop=True)
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
    # LF explicitly: pandas would otherwise use the platform's line ending, so the
    # same data would write differently on Windows and Linux.
    frame.sort_values("rec_id")[["rec_id"] + FEBRL_COLUMNS].to_csv(
        path, index=False, lineterminator="\n"
    )


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
        con.execute(
            f"""
            CREATE OR REPLACE TABLE {GROUND_TRUTH_TABLE} AS
            SELECT
                cluster_size,
                COUNT(*) AS entity_count,
                cluster_size * COUNT(*) AS record_count
            FROM (
                SELECT true_cluster_id, COUNT(*) AS cluster_size
                FROM {TABLE_NAME}
                GROUP BY true_cluster_id
            )
            GROUP BY cluster_size
            ORDER BY cluster_size
            """
        )

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
