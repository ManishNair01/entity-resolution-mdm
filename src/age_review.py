"""Phase 2 — route extreme ages to a review table.

The bands, the reference date and the table name come from the `age_review:`
section of `config/dq_rules.yaml` (AGENTS.md architecture rule 2). This module owns
the mechanism only.

Age is completed years on the fixed reference date, never the run date, so band
membership is the same on every run (architecture rule 4). It is computed from the
standardized date of birth alone: a DOB that was missing or impossible is NULL
there and never reaches a band.

The output table references customers by `unique_id`; it does not copy them. A
flagged customer stays in `std_customers` and stays eligible for matching. Whether
a pending review blocks an automatic merge is a Phase 5 decision.
"""

from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path
from typing import Any

import duckdb

from src.dq_rules import CONFIG_PATH, STAGE_PATTERN, load_config, sql_literal
from src.ingest import DEFAULT_DB_PATH, write_metrics
from src.standardize import TABLE_NAME as STD_TABLE

REQUIRED_KEYS = (
    "source_field",
    "standardized_field",
    "reference_date",
    "output_table",
    "initial_status",
    "bands",
)
IDENTIFIER_PATTERN = STAGE_PATTERN


def _identifier(value: Any, what: str) -> str:
    if not isinstance(value, str) or not IDENTIFIER_PATTERN.match(value):
        raise ValueError(f"age_review: {what} {value!r} must be a lowercase identifier")
    return value


def validate_config(section: Any) -> dict[str, Any]:
    """Check the `age_review:` section's shape before any SQL runs."""
    if not isinstance(section, dict):
        raise ValueError("age_review must be a mapping")
    missing = [key for key in REQUIRED_KEYS if key not in section]
    if missing:
        raise ValueError(f"age_review is missing {', '.join(missing)}")

    _identifier(section["standardized_field"], "standardized_field")
    _identifier(section["output_table"], "output_table")
    try:
        date.fromisoformat(str(section["reference_date"]))
    except ValueError as error:
        raise ValueError(f"age_review: reference_date must be YYYY-MM-DD: {error}") from error

    bands = section["bands"]
    if not isinstance(bands, list) or not bands:
        raise ValueError("age_review: 'bands' must be a non-empty list")
    reasons: set[str] = set()
    for band in bands:
        if not isinstance(band, dict) or "reason" not in band:
            raise ValueError(f"each band needs a 'reason': {band!r}")
        if band["reason"] in reasons:
            raise ValueError(f"duplicate band reason {band['reason']!r}")
        reasons.add(band["reason"])
        low, high = band.get("minimum_age"), band.get("maximum_age")
        if low is None and high is None:
            raise ValueError(f"band {band['reason']!r} needs minimum_age or maximum_age")
        for bound in (low, high):
            if bound is not None and (isinstance(bound, bool) or not isinstance(bound, int)):
                raise ValueError(f"band {band['reason']!r}: ages must be whole numbers")
        if low is not None and high is not None and low > high:
            raise ValueError(f"band {band['reason']!r}: minimum_age is above maximum_age")
    return section


def band_condition(band: dict[str, Any]) -> str:
    """SQL over `age` that is TRUE when the age falls inside the band, ends included."""
    parts = []
    if band.get("minimum_age") is not None:
        parts.append(f"age >= {int(band['minimum_age'])}")
    if band.get("maximum_age") is not None:
        parts.append(f"age <= {int(band['maximum_age'])}")
    return " AND ".join(parts)


def run(db_path: Path | str = DEFAULT_DB_PATH, config_path: Path | str = CONFIG_PATH) -> dict:
    """Write the age-review table from `std_customers` and return this stage's metrics."""
    config = load_config(config_path)
    if not config.get("age_review"):
        # No section means the owner has not asked for this review; that is not an
        # error, and the metrics say so rather than implying zero flagged records.
        return {}
    section = validate_config(config["age_review"])

    table = section["output_table"]
    std_field = section["standardized_field"]
    reference = date.fromisoformat(str(section["reference_date"]))
    bands = section["bands"]

    band_rows = " UNION ALL ".join(
        f"SELECT {sql_literal(band['reason'])} AS reason, "
        f"{int(band['minimum_age']) if band.get('minimum_age') is not None else 'NULL'} AS minimum_age, "
        f"{int(band['maximum_age']) if band.get('maximum_age') is not None else 'NULL'} AS maximum_age"
        for band in bands
    )

    with duckdb.connect(str(db_path)) as con:
        # `date_sub('year', ...)` counts completed years; `date_diff` would count
        # calendar-year boundaries and put a December birthday a year too old.
        con.execute(
            f"""
            CREATE OR REPLACE TABLE {table} AS
            WITH aged AS (
                SELECT
                    unique_id,
                    date_sub('year', CAST({std_field} AS DATE), ?::DATE) AS age
                FROM {STD_TABLE}
                WHERE {std_field} IS NOT NULL
            ),
            bands AS ({band_rows})
            SELECT
                aged.unique_id,
                aged.age AS calculated_age,
                ?::DATE AS calculation_date,
                bands.reason,
                ? AS status
            FROM aged
            JOIN bands
              ON (bands.minimum_age IS NULL OR aged.age >= bands.minimum_age)
             AND (bands.maximum_age IS NULL OR aged.age <= bands.maximum_age)
            ORDER BY aged.unique_id, bands.reason
            """,
            [reference.isoformat(), reference.isoformat(), section["initial_status"]],
        )
        total = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        by_reason = {
            reason: int(count)
            for reason, count in con.execute(
                f"SELECT reason, COUNT(*) FROM {table} GROUP BY reason"
            ).fetchall()
        }

    metrics = {
        "age_review.reference_date": reference.isoformat(),
        "age_review.flagged_count": int(total),
        # A band that flagged nobody is a result, so it is reported as zero.
        "age_review.flagged_by_reason": {
            band["reason"]: by_reason.get(band["reason"], 0) for band in bands
        },
    }
    write_metrics(metrics)
    return metrics


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default=str(DEFAULT_DB_PATH), help="path to the DuckDB file")
    parser.add_argument("--config", default=str(CONFIG_PATH), help="path to dq_rules.yaml")
    args = parser.parse_args()

    for key, value in run(args.db, args.config).items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
