"""Phase 3, Part A — the deterministic baseline matcher.

Each variant in `config/baseline.yaml` declares two records a match when every field
it lists is equal and present. For each variant this stage writes one pair table,
`baseline_pairs_<id>`, in the contract described in `src/pairs.py`. Scoring those
pairs against ground truth (precision, recall, F1) is `src/evaluate.py`'s job and is
owner-written, so this stage reports only what needs no labels: how many pairs each
variant declares a match.

The baseline exists to show why exact-match rules fail on messy data, which is what
justifies the probabilistic model in Phase 4. It is deliberately simple.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import duckdb

from src import pairs
from src.dq_rules import PROJECT_ROOT, table_columns
from src.ingest import DEFAULT_DB_PATH, remove_metrics, write_metrics
from src.standardize import TABLE_NAME as STD_TABLE

CONFIG_PATH = PROJECT_ROOT / "config" / "baseline.yaml"
TABLE_PREFIX = "baseline_pairs_"
METRIC_PREFIX = "baseline."


def load_variants(
    config_path: Path | str = CONFIG_PATH, columns: set[str] | None = None
) -> list[tuple[str, list[tuple[str, int | None]]]]:
    """Return `(id, keys)` for every variant, validated before any SQL runs.

    `match_on` lists whole columns only; comparing a prefix is a blocking device and
    is not offered here.
    """
    config = pairs.load_yaml(config_path)
    if "variants" not in config:
        raise ValueError("baseline config is missing 'variants'")
    variants: list[dict[str, Any]] = pairs.check_entries(config["variants"], "variants")
    out = []
    for variant in variants:
        if "match_on" not in variant:
            raise ValueError(f"variant {variant['id']!r} is missing match_on")
        match_on = variant["match_on"]
        if not isinstance(match_on, list) or not all(isinstance(item, str) for item in match_on):
            raise ValueError(f"variant {variant['id']!r}: match_on must list column names")
        out.append((variant["id"], pairs.parse_keys(match_on, columns)))
    return out


def run(
    db_path: Path | str = DEFAULT_DB_PATH,
    config_path: Path | str = CONFIG_PATH,
    source_table: str = STD_TABLE,
) -> dict:
    """Write one pair table per variant and return this stage's metrics.

    The pipeline and CLI read matching_customers. Direct callers retain the
    checked std_customers default for compatibility; invalid evidence still
    raises before output changes.
    """
    if source_table not in {STD_TABLE, "matching_customers"}:
        raise ValueError("source_table must be std_customers or matching_customers")
    with duckdb.connect(str(db_path)) as con:
        columns = table_columns(con, source_table)
        if not columns:
            raise ValueError(f"table {source_table!r} does not exist in {db_path}")
        variants = load_variants(config_path, columns)
        pairs.assert_inputs_usable(
            con, {field for _, keys in variants for field, _ in keys}, source_table
        )

        # Everything above can refuse; only now is the previous run's output replaced.
        remove_metrics(METRIC_PREFIX)
        pairs.drop_tables_with_prefix(con, TABLE_PREFIX)
        matched = {
            variant_id: pairs.write_pairs(
                con, f"{TABLE_PREFIX}{variant_id}", pairs.pairs_select(source_table, keys)
            )
            for variant_id, keys in variants
        }

    metrics = {
        "baseline.variant_count": len(variants),
        # A variant that matched nothing is a result, so it is reported as zero.
        "baseline.matched_pairs_by_variant": matched,
    }
    write_metrics(metrics)
    return metrics


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default=str(DEFAULT_DB_PATH), help="path to the DuckDB file")
    parser.add_argument("--config", default=str(CONFIG_PATH), help="path to baseline.yaml")
    args = parser.parse_args()

    for key, value in run(args.db, args.config, source_table="matching_customers").items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
