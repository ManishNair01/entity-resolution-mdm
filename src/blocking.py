"""Phase 3, Part B — candidate blocking rules and their label-free costs.

Comparing every record with every other costs n(n-1)/2 comparisons. Each rule in
`config/blocking.yaml` keeps only the pairs that agree on its keys. For each rule
this stage writes a pair table, `blocking_pairs_<id>`, plus `blocking_pairs_union`
for the pairs any rule produces, all in the contract described in `src/pairs.py`.

What it reports needs no labels: the candidate pairs each rule (and the union)
generates, and the reduction ratio against the full comparison. **Pair
completeness** — the share of true duplicate pairs that survive blocking — needs
ground truth, so it is `src/evaluate.py`'s job and is owner-written. Blocking can
only lose true matches, never add them, so that number is the ceiling on recall.
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

CONFIG_PATH = PROJECT_ROOT / "config" / "blocking.yaml"
TABLE_PREFIX = "blocking_pairs_"
UNION_ID = "union"
UNION_TABLE = f"{TABLE_PREFIX}{UNION_ID}"
METRIC_PREFIX = "blocking."


def load_rules(
    config_path: Path | str = CONFIG_PATH, columns: set[str] | None = None
) -> list[tuple[str, list[tuple[str, int | None]]]]:
    """Return `(id, keys)` for every rule, validated before any SQL runs."""
    config = pairs.load_yaml(config_path)
    if "rules" not in config:
        raise ValueError("blocking config is missing 'rules'")
    rules: list[dict[str, Any]] = pairs.check_entries(
        config["rules"], "rules", reserved=(UNION_ID,)
    )
    out = []
    for rule in rules:
        if "keys" not in rule:
            raise ValueError(f"rule {rule['id']!r} is missing keys")
        out.append((rule["id"], pairs.parse_keys(rule["keys"], columns)))
    return out


def run(
    db_path: Path | str = DEFAULT_DB_PATH,
    config_path: Path | str = CONFIG_PATH,
    source_table: str = STD_TABLE,
) -> dict:
    """Write one pair table per rule and the union, and return this stage's metrics.

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
        rules = load_rules(config_path, columns)
        pairs.assert_inputs_usable(con, {field for _, keys in rules for field, _ in keys}, source_table)

        # Everything above can refuse; only now is the previous run's output replaced.
        remove_metrics(METRIC_PREFIX)
        pairs.drop_tables_with_prefix(con, TABLE_PREFIX)

        records = pairs.record_count(con, source_table)
        full = pairs.full_pair_count(records)
        candidates = {
            rule_id: pairs.write_pairs(
                con, f"{TABLE_PREFIX}{rule_id}", pairs.pairs_select(source_table, keys)
            )
            for rule_id, keys in rules
        }

        if rules:
            parts = " UNION ALL ".join(
                f"SELECT unique_id_l, unique_id_r FROM {TABLE_PREFIX}{rule_id}"
                for rule_id, _ in rules
            )
            union = pairs.write_pairs(
                con,
                UNION_TABLE,
                f"SELECT DISTINCT unique_id_l, unique_id_r FROM ({parts}) "
                "ORDER BY unique_id_l, unique_id_r",
            )
        else:
            con.execute(
                f"CREATE OR REPLACE TABLE {UNION_TABLE} (unique_id_l BIGINT, unique_id_r BIGINT)"
            )
            union = 0

    metrics = {
        "blocking.record_count": records,
        "blocking.full_pair_count": full,
        "blocking.rule_count": len(rules),
        "blocking.candidate_pairs_by_rule": candidates,
        "blocking.reduction_ratio_by_rule": {
            rule_id: pairs.reduction_ratio(count, full) for rule_id, count in candidates.items()
        },
        "blocking.union_candidate_pairs": union,
        "blocking.union_reduction_ratio": pairs.reduction_ratio(union, full),
    }
    write_metrics(metrics)
    return metrics


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default=str(DEFAULT_DB_PATH), help="path to the DuckDB file")
    parser.add_argument("--config", default=str(CONFIG_PATH), help="path to blocking.yaml")
    args = parser.parse_args()

    for key, value in run(args.db, args.config, source_table="matching_customers").items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
