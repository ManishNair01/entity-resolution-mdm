"""Phase 2 — apply the owner's standardization steps and write `std_customers`.

Which fields get cleaned, and how, comes entirely from the `standardization:`
section of `config/dq_rules.yaml` (AGENTS.md architecture rule 2). What this
module owns is the mechanism: the set of transforms a step may use, and the
DuckDB expression each one compiles to.

Cleaned values land in new `<field>_std` columns and every original column is
carried through untouched, so a rule can be evaluated before and after cleaning
and no information is lost (roadmap Phase 2: "Keep original values alongside
cleaned ones").

The transforms normalize *representation* only. None of them decides that two
different values are the same person; that is matching, and it starts in Phase 3.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Any, Callable

import duckdb

from src.dq_rules import (
    CONFIG_PATH,
    WHITESPACE,
    load_config,
    sql_literal,
    strict_date_sql,
    trim_sql,
)
from src.ingest import DEFAULT_DB_PATH, FEBRL_COLUMNS, TABLE_NAME as SOURCE_TABLE, write_metrics

TABLE_NAME = "std_customers"

# Columns copied through from the source table. The guarded ground-truth columns
# are deliberately not among them: hard rule 1 keeps them out of everything
# downstream, and `evaluate.py` can join them back on `unique_id` when it scores
# results. The two synthetic metadata columns are carried because survivorship
# needs them in Phase 6.
CARRIED_COLUMNS = ["unique_id", *FEBRL_COLUMNS, "source_system", "last_updated"]

STD_SUFFIX = "_std"


def _trim(expr: str, step: dict[str, Any]) -> str:
    """Strip surrounding whitespace of every kind, not just spaces (`dq_rules.WHITESPACE`)."""
    return trim_sql(expr)


def _collapse_whitespace(expr: str, step: dict[str, Any]) -> str:
    return f"regexp_replace({expr}, {sql_literal(WHITESPACE + '+')}, ' ', 'g')"


def _lowercase(expr: str, step: dict[str, Any]) -> str:
    return f"LOWER({expr})"


def _strip_non_digits(expr: str, step: dict[str, Any]) -> str:
    return f"regexp_replace({expr}, '[^0-9]', '', 'g')"


def _normalize_date(expr: str, step: dict[str, Any]) -> str:
    """Reformat a date, leaving values that don't parse alone unless told otherwise.

    `on_error: keep` (the default) is the conservative reading: an unparseable
    date is a fact about the data for a validity rule to flag, not something this
    stage should quietly turn into NULL. `on_error: null` blanks it instead.

    Parsing is strict (`dq_rules.strict_date_sql`): a value that is not exactly
    `from_format`, such as a seven-digit `1970011` or a padded `' 19700101'`, counts
    as unparseable rather than being guessed into a date.
    """
    from_format = _required(step, "from_format")
    to_format = _required(step, "to_format")
    on_error = step.get("on_error", "keep")
    if on_error is None:
        # An unquoted `on_error: null` in YAML loads as None, not the string.
        on_error = "null"
    if on_error not in ("keep", "null"):
        raise ValueError(f"normalize_date: on_error must be 'keep' or 'null', got {on_error!r}")

    parsed = f"strftime({strict_date_sql(expr, from_format)}, {sql_literal(to_format)})"
    return parsed if on_error == "null" else f"COALESCE({parsed}, {expr})"


def _map_values(expr: str, step: dict[str, Any]) -> str:
    """Replace whole values via a lookup, leaving anything unlisted as it is.

    The match is exact against the value as it stands at this point in the chain,
    so a `trim` / `lowercase` step belongs before this one.
    """
    mapping = _required(step, "mapping")
    if not isinstance(mapping, dict) or not mapping:
        raise ValueError("map_values: 'mapping' must be a non-empty mapping")
    whens = " ".join(
        f"WHEN {sql_literal(key)} THEN {sql_literal(value)}" for key, value in mapping.items()
    )
    return f"CASE {expr} {whens} ELSE {expr} END"


def _replace_words(expr: str, step: dict[str, Any]) -> str:
    """Replace whole words inside a value, e.g. `vlge` -> `village` in an address.

    Word boundaries matter: replacing the substring `st` would turn `street` into
    `streeet`-shaped nonsense and `castle` into something else again. Keys are
    regex-escaped, and the steps apply in the order they are written in the
    config, which keeps the output reproducible.
    """
    mapping = _required(step, "mapping")
    if not isinstance(mapping, dict) or not mapping:
        raise ValueError("replace_words: 'mapping' must be a non-empty mapping")
    out = expr
    for key, value in mapping.items():
        pattern = rf"\b{re.escape(str(key))}\b"
        out = f"regexp_replace({out}, {sql_literal(pattern)}, {sql_literal(value)}, 'g')"
    return out


def _replace_phrases(expr: str, step: dict[str, Any]) -> str:
    """Replace whole multi-word phrases, e.g. the split `st reet` -> `street`.

    Same boundary and ordering rules as `replace_words`; the phrase is matched
    with single spaces, so put `collapse_whitespace` earlier in the chain.
    """
    mapping = _required(step, "mapping")
    if not isinstance(mapping, dict) or not mapping:
        raise ValueError("replace_phrases: 'mapping' must be a non-empty mapping")
    out = expr
    for key, value in mapping.items():
        pattern = rf"\b{re.escape(str(key))}\b"
        out = f"regexp_replace({out}, {sql_literal(pattern)}, {sql_literal(value)}, 'g')"
    return out


def _replace_contextual_word(expr: str, step: dict[str, Any]) -> str:
    """Expand one abbreviation by position: `st` is `saint` first, `street` elsewhere.

    `at_start` replaces the word when it opens the value; `otherwise` replaces it
    everywhere else. The start is handled first, and its replacement is a
    different word, so it is not then rewritten by the second pass.
    """
    word = str(_required(step, "word"))
    at_start = _required(step, "at_start")
    otherwise = _required(step, "otherwise")
    start_pattern = "^" + re.escape(word) + r"\b"
    anywhere_pattern = r"\b" + re.escape(word) + r"\b"
    at_start_pass = f"regexp_replace({expr}, {sql_literal(start_pattern)}, {sql_literal(at_start)})"
    return (
        f"regexp_replace({at_start_pass}, {sql_literal(anywhere_pattern)}, "
        f"{sql_literal(otherwise)}, 'g')"
    )


TRANSFORMS: dict[str, Callable[[str, dict[str, Any]], str]] = {
    "trim": _trim,
    "collapse_whitespace": _collapse_whitespace,
    "lowercase": _lowercase,
    "strip_non_digits": _strip_non_digits,
    "normalize_date": _normalize_date,
    "map_values": _map_values,
    "replace_words": _replace_words,
    "replace_phrases": _replace_phrases,
    "replace_contextual_word": _replace_contextual_word,
}


def _required(step: dict[str, Any], key: str) -> Any:
    if key not in step:
        raise ValueError(f"{step.get('type', 'step')}: missing required key {key!r}")
    return step[key]


def transform_expr(expr: str, step: dict[str, Any]) -> str:
    """Wrap `expr` in one transform, chosen by the step's `type`."""
    if not isinstance(step, dict) or "type" not in step:
        raise ValueError(f"standardization step must be a mapping with a 'type': {step!r}")
    step_type = step["type"]
    if step_type not in TRANSFORMS:
        known = ", ".join(sorted(TRANSFORMS))
        raise ValueError(f"unknown standardization type {step_type!r}; known types: {known}")
    return TRANSFORMS[step_type](expr, step)


def field_expr(field: str, steps: list[dict[str, Any]]) -> str:
    """Compile one field's whole chain of steps into a single SQL expression."""
    expr = f"CAST({field} AS VARCHAR)"
    for step in steps:
        expr = transform_expr(expr, step)
    return expr


def standardized_fields(config: dict[str, Any]) -> list[tuple[str, str]]:
    """Return `(field, sql_expression)` for every field the config standardizes."""
    out: list[tuple[str, str]] = []
    seen: set[str] = set()
    for entry in config.get("standardization") or []:
        if not isinstance(entry, dict) or "field" not in entry:
            raise ValueError(f"standardization entry needs a 'field': {entry!r}")
        field = entry["field"]
        if field in seen:
            raise ValueError(f"field {field!r} is standardized twice; merge the steps")
        seen.add(field)
        out.append((field, field_expr(field, entry.get("steps") or [])))
    return out


def select_sql(fields: list[tuple[str, str]]) -> str:
    """Build the SELECT that produces `std_customers`."""
    columns = list(CARRIED_COLUMNS)
    columns += [f"{expr} AS {field}{STD_SUFFIX}" for field, expr in fields]
    return (
        f"SELECT {', '.join(columns)} FROM {SOURCE_TABLE} ORDER BY unique_id"  # noqa: S608
    )


def run(db_path: Path | str = DEFAULT_DB_PATH, config_path: Path | str = CONFIG_PATH) -> dict:
    """Write `std_customers` and return this stage's metrics.

    Writes a new table and never touches the source one (AGENTS.md architecture
    rule 1). With no standardization configured, the table is the carried columns
    and nothing else, which is a valid — if empty — Phase 2 output.
    """
    config = load_config(config_path)
    fields = standardized_fields(config)

    with duckdb.connect(str(db_path)) as con:
        con.execute(f"CREATE OR REPLACE TABLE {TABLE_NAME} AS {select_sql(fields)}")
        row_count = con.execute(f"SELECT COUNT(*) FROM {TABLE_NAME}").fetchone()[0]
        changed = {}
        for field, _ in fields:
            changed[field] = int(
                con.execute(
                    f"SELECT COUNT(*) FROM {TABLE_NAME} "
                    f"WHERE {field}{STD_SUFFIX} IS DISTINCT FROM CAST({field} AS VARCHAR)"
                ).fetchone()[0]
            )

    metrics = {
        "standardize.row_count": int(row_count),
        "standardize.standardized_field_count": len(fields),
        # Per field: how many rows the cleaning actually changed. Zero across the
        # board means the steps are no-ops on this data, which is worth knowing.
        "standardize.changed_by_field": changed,
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
