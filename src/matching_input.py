"""Build label-free matching input, masking DQ-invalid standardized evidence.

All records survive. Source and standardized tables remain untouched. The column
allowlist comes from configured standardization outputs plus the opaque row ID.
Validity rules are evaluated by dq_std; this stage consumes those flags.
"""
from pathlib import Path

import duckdb

from src import dq_rules, ingest, standardize

TABLE_NAME = "matching_customers"


def run(db_path: Path | str = ingest.DEFAULT_DB_PATH,
        config_path: Path | str = dq_rules.CONFIG_PATH) -> dict:
    config = dq_rules.load_config(config_path)
    fields = [field + standardize.STD_SUFFIX
              for field, _ in standardize.standardized_fields(config)]
    with duckdb.connect(str(db_path)) as con:
        columns = dq_rules.table_columns(con, standardize.TABLE_NAME)
        if not {"unique_id", *fields}.issubset(columns):
            raise ValueError("std_customers is missing configured matching columns")
        if not dq_rules.table_columns(con, "dq_violations_std"):
            raise ValueError("run dq_std before building matching input")
        expressions = ["s.unique_id"]
        masked = {}
        for field in fields:
            invalid = (
                "EXISTS (SELECT 1 FROM dq_violations_std v "
                "WHERE v.unique_id = s.unique_id AND v.dimension = 'validity' "
                f"AND v.field = {dq_rules.sql_literal(field)})"
            )
            expressions.append(f"CASE WHEN {invalid} THEN NULL ELSE s.{field} END AS {field}")
            masked[field] = con.execute(
                f"SELECT count(*) FROM {standardize.TABLE_NAME} s "
                f"WHERE s.{field} IS NOT NULL AND {invalid}"
            ).fetchone()[0]
        con.execute(
            f"CREATE OR REPLACE TABLE {TABLE_NAME} AS SELECT "
            + ", ".join(expressions)
            + f" FROM {standardize.TABLE_NAME} s ORDER BY s.unique_id"
        )
        records = con.execute(f"SELECT count(*) FROM {TABLE_NAME}").fetchone()[0]
    metrics = {
        "matching_input.record_count": records,
        "matching_input.masked_values_by_field": masked,
    }
    ingest.write_metrics(metrics)
    return metrics
