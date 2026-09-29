"""Phase 2 — evaluate the owner's data-quality rules and write the violations tables.

The rules live in `config/dq_rules.yaml` and nowhere else, so adding, changing or
removing one needs no change here (AGENTS.md architecture rule 2). What this
module owns is the mechanism: which kinds of check a rule may use, the DuckDB
predicate each one compiles to, and where violations are recorded.

Two conventions worth being able to defend:

* **NULL passes every check except `not_null`.** A missing value is then one
  completeness violation, not one violation for every validity rule that happens
  to read the same field. A field is mandatory only if the owner gives it a
  `not_null` rule.
* **Nothing is dropped or corrected here.** A rule records a violation with the
  offending value and its severity; deciding what to do about it is a separate,
  explicit step.

The stage runs twice — once over `raw_customers`, once over `std_customers` — and
writes one table per pass (`dq_violations_raw`, `dq_violations_std`), which is
how Phase 2's before-and-after counts stay comparable without either pass
overwriting the other. In the second pass a rule on `state` reads `state_std`
when that column exists, so the two numbers describe the same rule against the
uncleaned and cleaned value.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Any, Callable

import duckdb
import yaml

from src.ingest import DEFAULT_DB_PATH, TABLE_NAME as RAW_TABLE, write_metrics

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = PROJECT_ROOT / "config" / "dq_rules.yaml"

DIMENSIONS = ("completeness", "validity", "standardization")
SEVERITIES = ("error", "warning")
REQUIRED_RULE_KEYS = ("id", "field", "dimension", "description", "severity", "check")

# Stage names become part of a table name, so they are restricted rather than
# interpolated as given.
STAGE_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")

STD_SUFFIX = "_std"


def sql_literal(value: Any) -> str:
    """Quote `value` as a DuckDB string literal.

    Config is data, not code: every value from the YAML reaches SQL through this
    function, so a quote inside a rule cannot end the literal early.
    """
    return "'" + str(value).replace("'", "''") + "'"


def load_config(path: Path | str = CONFIG_PATH) -> dict[str, Any]:
    """Load `config/dq_rules.yaml`.

    A missing file is an error rather than an empty config: silently evaluating
    zero rules would look exactly like a clean dataset.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"no DQ config at {path}")
    config = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(config, dict):
        raise ValueError(f"{path} must contain a mapping at the top level")
    return config


def _required(spec: dict[str, Any], key: str) -> Any:
    if key not in spec:
        raise ValueError(f"check {spec.get('type', '?')!r}: missing required key {key!r}")
    return spec[key]


def _not_null(field: str, spec: dict[str, Any]) -> str:
    return f"{field} IS NOT NULL"


def _not_blank(field: str, spec: dict[str, Any]) -> str:
    return f"{field} IS NULL OR TRIM(CAST({field} AS VARCHAR)) <> ''"


def _present(field: str, spec: dict[str, Any]) -> str:
    """A value is present when it is neither NULL nor whitespace only.

    Unlike the other checks this one fails on NULL: it is the completeness check.
    """
    return f"{field} IS NOT NULL AND TRIM(CAST({field} AS VARCHAR)) <> ''"


def _in_set(field: str, spec: dict[str, Any]) -> str:
    values = _required(spec, "values")
    if not isinstance(values, (list, tuple)) or not values:
        raise ValueError("in_set: 'values' must be a non-empty list")
    if spec.get("case_sensitive", False):
        subject = f"CAST({field} AS VARCHAR)"
        literals = ", ".join(sql_literal(value) for value in values)
    else:
        subject = f"LOWER(TRIM(CAST({field} AS VARCHAR)))"
        literals = ", ".join(sql_literal(str(value).strip().lower()) for value in values)
    return f"{field} IS NULL OR {subject} IN ({literals})"


def _matches_regex(field: str, spec: dict[str, Any]) -> str:
    pattern = _required(spec, "pattern")
    return (
        f"{field} IS NULL OR "
        f"regexp_matches(CAST({field} AS VARCHAR), {sql_literal(pattern)})"
    )


def _length_between(field: str, spec: dict[str, Any]) -> str:
    minimum = int(_required(spec, "min"))
    maximum = int(_required(spec, "max"))
    if minimum > maximum:
        raise ValueError(f"length_between: min {minimum} is greater than max {maximum}")
    return (
        f"{field} IS NULL OR "
        f"LENGTH(CAST({field} AS VARCHAR)) BETWEEN {minimum} AND {maximum}"
    )


def _parses_as_date(field: str, spec: dict[str, Any]) -> str:
    date_format = _required(spec, "format")
    return (
        f"{field} IS NULL OR "
        f"try_strptime(CAST({field} AS VARCHAR), {sql_literal(date_format)}) IS NOT NULL"
    )


# Each entry returns SQL that is TRUE when the value is acceptable; the engine
# records the rows where it is not.
CHECK_TYPES: dict[str, Callable[[str, dict[str, Any]], str]] = {
    "not_null": _not_null,
    "present": _present,
    "not_blank": _not_blank,
    "in_set": _in_set,
    "matches_regex": _matches_regex,
    "length_between": _length_between,
    "parses_as_date": _parses_as_date,
}


def check_predicate(field: str, spec: Any) -> str:
    """Compile one rule's `check` into a DuckDB predicate over `field`."""
    if not isinstance(spec, dict) or "type" not in spec:
        raise ValueError(f"check must be a mapping with a 'type': {spec!r}")
    check_type = spec["type"]
    if check_type not in CHECK_TYPES:
        known = ", ".join(sorted([*CHECK_TYPES, *RECORD_CHECK_TYPES]))
        raise ValueError(f"unknown check type {check_type!r}; known types: {known}")
    return CHECK_TYPES[check_type](field, spec)


def for_column(spec: dict[str, Any], standardized: bool) -> dict[str, Any]:
    """Return `spec` adjusted for the column it will read.

    A date check names the raw format (`format`) and, optionally, the format the
    cleaned column uses (`standardized_format`). When the rule is reading a
    `<field>_std` column the second replaces the first, so one rule gives a
    before and an after number for the same field.
    """
    if standardized and "standardized_format" in spec:
        return {**spec, "format": spec["standardized_format"]}
    return spec


def _usable(
    field: str, usable_when: Any, columns: set[str] | None
) -> tuple[str, str]:
    """Return `(column, predicate)`; the predicate is TRUE when the value is usable.

    Usable means present *and* passing the check, so a NULL is never usable even
    for checks that let NULL pass on their own.
    """
    column = resolve_field(field, columns) if columns is not None else field
    spec = for_column(usable_when, column != field)
    return column, f"({column} IS NOT NULL AND ({check_predicate(column, spec)}))"


def _minimum_identity_evidence(
    spec: dict[str, Any], columns: set[str] | None
) -> tuple[str, str]:
    """Record-level check: enough independent identity signals remain usable.

    Counts the usable `primary` fields, adds the usable `substitutes` capped at
    `max_substitutes`, and requires the total to reach `minimum_signals`. Returns
    `(predicate, value_sql)`; the value recorded is the signal count.
    """
    minimum = int(_required(spec, "minimum_signals"))
    max_substitutes = int(spec.get("max_substitutes", 0))
    if minimum < 1 or max_substitutes < 0:
        raise ValueError("minimum_identity_evidence: minimum_signals >= 1 and max_substitutes >= 0")

    def signals(key: str, required: bool) -> list[str]:
        entries = _required(spec, key) if required else spec.get(key) or []
        if not isinstance(entries, list) or (required and not entries):
            raise ValueError(f"minimum_identity_evidence: {key!r} must be a non-empty list")
        out = []
        for entry in entries:
            if not isinstance(entry, dict) or "field" not in entry or "usable_when" not in entry:
                raise ValueError(f"{key} entries need 'field' and 'usable_when': {entry!r}")
            _, predicate = _usable(entry["field"], entry["usable_when"], columns)
            out.append(f"(CASE WHEN {predicate} THEN 1 ELSE 0 END)")
        return out

    primary = signals("primary", required=True)
    substitutes = signals("substitutes", required=False)
    count = " + ".join(primary)
    if substitutes:
        count += f" + LEAST({max_substitutes}, {' + '.join(substitutes)})"
    return f"({count}) >= {minimum}", f"'usable_signals=' || CAST(({count}) AS VARCHAR)"


# Rules that read several columns of one record. Each entry takes the check spec
# and the table's columns (None while only validating) and returns
# `(predicate, value_sql)`.
RECORD_CHECK_TYPES: dict[str, Callable[[dict[str, Any], set[str] | None], tuple[str, str]]] = {
    "minimum_identity_evidence": _minimum_identity_evidence,
}


def compile_rule(
    rule: dict[str, Any], columns: set[str] | None = None
) -> tuple[str, str, str]:
    """Compile a rule to `(field label, predicate, value SQL)` for one table.

    With `columns` given, a field reads its `<field>_std` column when the table
    has one. With `columns=None` the rule is only being validated.
    """
    check = rule["check"]
    if isinstance(check, dict) and check.get("type") in RECORD_CHECK_TYPES:
        predicate, value_sql = RECORD_CHECK_TYPES[check["type"]](check, columns)
        return rule["field"], predicate, value_sql
    field = resolve_field(rule["field"], columns) if columns is not None else rule["field"]
    spec = for_column(check, field != rule["field"]) if isinstance(check, dict) else check
    return field, check_predicate(field, spec), f"CAST({field} AS VARCHAR)"


def validate_rules(config: dict[str, Any]) -> list[dict[str, Any]]:
    """Check every rule's shape up front, so a typo fails before any SQL runs."""
    rules = config.get("rules") or []
    if not isinstance(rules, list):
        raise ValueError("'rules' must be a list")

    seen: set[str] = set()
    for rule in rules:
        if not isinstance(rule, dict):
            raise ValueError(f"each rule must be a mapping: {rule!r}")
        missing = [key for key in REQUIRED_RULE_KEYS if key not in rule]
        if missing:
            raise ValueError(f"rule {rule.get('id', '?')!r} is missing {', '.join(missing)}")
        if rule["id"] in seen:
            raise ValueError(f"duplicate rule id {rule['id']!r}")
        seen.add(rule["id"])
        if rule["dimension"] not in DIMENSIONS:
            raise ValueError(
                f"rule {rule['id']!r}: dimension must be one of {', '.join(DIMENSIONS)}"
            )
        if rule["severity"] not in SEVERITIES:
            raise ValueError(
                f"rule {rule['id']!r}: severity must be one of {', '.join(SEVERITIES)}"
            )
        # Compile now to surface a bad check type or a missing parameter here.
        compile_rule(rule)
    return rules


def table_columns(con: duckdb.DuckDBPyConnection, table: str) -> set[str]:
    rows = con.execute(
        "SELECT column_name FROM information_schema.columns WHERE table_name = ?", [table]
    ).fetchall()
    return {row[0] for row in rows}


def resolve_field(field: str, columns: set[str]) -> str:
    """Read the cleaned column when the table has one, otherwise the original.

    This is what makes the before/after comparison honest: the same rule is
    evaluated against `state` in the raw pass and `state_std` in the cleaned one.
    """
    candidate = f"{field}{STD_SUFFIX}"
    if candidate in columns:
        return candidate
    if field not in columns:
        raise ValueError(f"field {field!r} is not a column of the table being checked")
    return field


def run_for(
    db_path: Path | str = DEFAULT_DB_PATH,
    source_table: str = RAW_TABLE,
    stage: str = "raw",
    config_path: Path | str = CONFIG_PATH,
) -> dict:
    """Evaluate every rule against `source_table` and write `dq_violations_<stage>`."""
    if not STAGE_PATTERN.match(stage):
        raise ValueError(f"stage {stage!r} must be a lowercase identifier")

    rules = validate_rules(load_config(config_path))
    violations_table = f"dq_violations_{stage}"

    with duckdb.connect(str(db_path)) as con:
        columns = table_columns(con, source_table)
        if not columns:
            raise ValueError(f"table {source_table!r} does not exist in {db_path}")

        con.execute(
            f"""
            CREATE OR REPLACE TABLE {violations_table} (
                unique_id BIGINT,
                rule_id VARCHAR,
                field VARCHAR,
                dimension VARCHAR,
                severity VARCHAR,
                value VARCHAR
            )
            """
        )

        for rule in rules:
            field, predicate, value_sql = compile_rule(rule, columns)
            con.execute(
                f"""
                INSERT INTO {violations_table}
                SELECT
                    unique_id,
                    {sql_literal(rule['id'])},
                    {sql_literal(field)},
                    {sql_literal(rule['dimension'])},
                    {sql_literal(rule['severity'])},
                    {value_sql}
                FROM {source_table}
                WHERE NOT ({predicate})
                ORDER BY unique_id
                """
            )

        by_rule = {
            rule_id: int(count)
            for rule_id, count in con.execute(
                f"SELECT rule_id, COUNT(*) FROM {violations_table} GROUP BY rule_id ORDER BY rule_id"
            ).fetchall()
        }
        total, records = con.execute(
            f"SELECT COUNT(*), COUNT(DISTINCT unique_id) FROM {violations_table}"
        ).fetchone()

    metrics = {
        f"dq.{stage}.rule_count": len(rules),
        f"dq.{stage}.total_violations": int(total),
        f"dq.{stage}.records_with_violations": int(records),
        # Rules that fired zero times are absent from the GROUP BY, so fill them
        # in: "this rule found nothing" is a result, not a missing number.
        f"dq.{stage}.violations_by_rule": {
            rule["id"]: by_rule.get(rule["id"], 0) for rule in rules
        },
    }
    write_metrics(metrics)
    return metrics


def run_raw(db_path: Path | str = DEFAULT_DB_PATH, config_path: Path | str = CONFIG_PATH) -> dict:
    """Pipeline entry point for the pass over the raw table."""
    return run_for(db_path, source_table=RAW_TABLE, stage="raw", config_path=config_path)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default=str(DEFAULT_DB_PATH), help="path to the DuckDB file")
    parser.add_argument("--config", default=str(CONFIG_PATH), help="path to dq_rules.yaml")
    parser.add_argument("--table", default=RAW_TABLE, help="table to check")
    parser.add_argument("--stage", default="raw", help="names the output table, dq_violations_<stage>")
    args = parser.parse_args()

    metrics = run_for(args.db, source_table=args.table, stage=args.stage, config_path=args.config)
    for key, value in metrics.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
