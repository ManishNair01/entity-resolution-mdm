"""Phase 3 — shared mechanism for the baseline matcher and the blocking rules.

Both stages turn a configured list of keys into the pairs of records that agree on
every key. That is the whole mechanism, so it lives here once. The rules themselves
(`config/baseline.yaml`, `config/blocking.yaml`) are the owner's; nothing in this
module names a field or a rule (AGENTS.md architecture rule 2).

The output contract, shared with the owner-written `src/evaluate.py`: a pair table
has exactly the columns `unique_id_l` and `unique_id_r`, every row is a canonical
unordered pair (`unique_id_l < unique_id_r`), there are no self-pairs and no
duplicates, and the rows are sorted. The tables hold opaque keys only; ground truth
never appears here, and scoring against it happens in `evaluate.py`.

Two conventions worth being able to defend:

* **Missing never equals missing.** A key that is NULL or an empty string takes no
  part in a pair, so two records that both lack a postcode are not "the same
  postcode". SQL equality already behaves this way for NULL; the empty string is
  folded into NULL so a blank cannot match another blank either.
* **A flag alone does not make a value usable.** A value that the data-quality
  stage flagged as invalid but that is still present would silently become a join
  key. The stage refuses to run in that case rather than choose how to handle it.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import duckdb
import yaml

from src.dq_rules import STAGE_PATTERN, sql_literal, table_columns
from src.standardize import TABLE_NAME as STD_TABLE

IDENTIFIER_PATTERN = STAGE_PATTERN
PAIR_COLUMNS = ("unique_id_l", "unique_id_r")
VIOLATIONS_TABLE = "dq_violations_std"


def load_yaml(path: Path | str) -> dict[str, Any]:
    """Load a rules file. A missing file is an error, never an empty rule set."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"no rules file at {path}")
    config = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(config, dict):
        raise ValueError(f"{path} must contain a mapping at the top level")
    return config


def check_entries(
    section: Any, name: str, reserved: tuple[str, ...] = ()
) -> list[dict[str, Any]]:
    """Check the shape shared by every entry: a unique lowercase `id` and a `description`.

    The id becomes part of a table name, so it is restricted rather than
    interpolated as given.
    """
    if section is None:
        return []
    if not isinstance(section, list):
        raise ValueError(f"'{name}' must be a list")
    seen: set[str] = set()
    for entry in section:
        if not isinstance(entry, dict):
            raise ValueError(f"each entry in '{name}' must be a mapping: {entry!r}")
        for key in ("id", "description"):
            if key not in entry:
                raise ValueError(f"entry {entry.get('id', '?')!r} in '{name}' is missing {key}")
        identifier = entry["id"]
        if not isinstance(identifier, str) or not IDENTIFIER_PATTERN.match(identifier):
            raise ValueError(f"{name}: id {identifier!r} must be a lowercase identifier")
        if identifier in reserved:
            raise ValueError(f"{name}: id {identifier!r} is reserved")
        if identifier in seen:
            raise ValueError(f"{name}: duplicate id {identifier!r}")
        seen.add(identifier)
    return section


def parse_key(key: Any, columns: set[str] | None = None) -> tuple[str, int | None]:
    """Return `(column, prefix_length)` for one key; `prefix_length` is None for a whole value.

    With `columns` given, the column must exist in the table being read, which is
    also what keeps a config value out of the SQL as anything but a real column name.
    """
    if isinstance(key, str):
        field, prefix = key, None
    elif isinstance(key, dict):
        unknown = set(key) - {"field", "prefix"}
        if unknown or "field" not in key:
            raise ValueError(f"a key needs 'field' and optionally 'prefix' only: {key!r}")
        field, prefix = key["field"], key.get("prefix")
        if prefix is not None and (isinstance(prefix, bool) or not isinstance(prefix, int) or prefix < 1):
            raise ValueError(f"key {field!r}: prefix must be a whole number of at least 1")
    else:
        raise ValueError(f"a key must be a column name or a mapping: {key!r}")
    if not isinstance(field, str) or not IDENTIFIER_PATTERN.match(field):
        raise ValueError(f"key field {field!r} must be a lowercase column name")
    if columns is not None and field not in columns:
        raise ValueError(f"key field {field!r} is not a column of {STD_TABLE}")
    return field, prefix


def parse_keys(keys: Any, columns: set[str] | None = None) -> list[tuple[str, int | None]]:
    """Parse a rule's whole key list. At least one key is required, or every record would pair."""
    if not isinstance(keys, list) or not keys:
        raise ValueError("a rule needs a non-empty list of keys")
    return [parse_key(key, columns) for key in keys]


def key_sql(alias: str, field: str, prefix: int | None) -> str:
    """SQL for one key of one record; NULL when the value is missing or blank."""
    value = f"CAST({alias}.{field} AS VARCHAR)"
    if prefix is not None:
        value = f"LEFT({value}, {int(prefix)})"
    return f"NULLIF({value}, '')"


def pairs_select(source_table: str, keys: list[tuple[str, int | None]]) -> str:
    """SELECT of every canonical pair that agrees on all `keys`, sorted."""
    agree = " AND ".join(
        f"{key_sql('l', field, prefix)} = {key_sql('r', field, prefix)}" for field, prefix in keys
    )
    return (
        f"SELECT l.unique_id AS unique_id_l, r.unique_id AS unique_id_r "
        f"FROM {source_table} AS l JOIN {source_table} AS r "
        f"ON l.unique_id < r.unique_id AND {agree} "
        f"ORDER BY unique_id_l, unique_id_r"
    )


def write_pairs(con: duckdb.DuckDBPyConnection, table: str, select: str) -> int:
    """Create `table` from `select` (replacing this stage's earlier copy); return its row count."""
    con.execute(f"CREATE OR REPLACE TABLE {table} AS {select}")
    return int(con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])


def drop_tables_with_prefix(con: duckdb.DuckDBPyConnection, prefix: str) -> None:
    """Drop every table whose name starts with `prefix`.

    A stage owns its whole prefix, so a rule removed or renamed in the config does
    not leave its old pair table behind looking current.
    """
    names = [
        row[0]
        for row in con.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE starts_with(table_name, ?) ORDER BY table_name",
            [prefix],
        ).fetchall()
    ]
    for name in names:
        con.execute('DROP TABLE "' + name.replace('"', '""') + '"')


def assert_inputs_usable(con: duckdb.DuckDBPyConnection, fields: set[str]) -> None:
    """Refuse to read a column whose present values DQ flagged as invalid.

    The std table makes an impossible date of birth NULL, but an invalid postcode
    or identifier keeps its source string and is only flagged in
    `dq_violations_std`. Reading such a column as a key would let a flagged value
    match. How to make it unavailable is the owner's call, so this stops instead.
    """
    if not table_columns(con, VIOLATIONS_TABLE):
        raise ValueError(f"{VIOLATIONS_TABLE} does not exist; run the dq_std stage first")
    if not fields:
        return
    listed = ", ".join(sql_literal(field) for field in sorted(fields))
    flagged = con.execute(
        f"SELECT field, COUNT(*) FROM {VIOLATIONS_TABLE} "
        f"WHERE dimension = 'validity' AND field IN ({listed}) GROUP BY field ORDER BY field"
    ).fetchall()
    if flagged:
        detail = ", ".join(f"{field}: {count}" for field, count in flagged)
        raise ValueError(
            "values flagged invalid by a validity rule are still present in a column the "
            f"rules read ({detail}); decide how to make them unavailable before matching "
            "(OPEN-DECISIONS.md item 15)"
        )


def record_count(con: duckdb.DuckDBPyConnection) -> int:
    return int(con.execute(f"SELECT COUNT(*) FROM {STD_TABLE}").fetchone()[0])


def full_pair_count(records: int) -> int:
    """Number of comparisons a full pairwise comparison would need: n(n-1)/2."""
    return records * (records - 1) // 2


def reduction_ratio(candidates: int, full_pairs: int) -> float | None:
    """Share of the full comparison avoided: 1 - candidates / full. None if there is nothing to compare."""
    if full_pairs == 0:
        return None
    return 1 - candidates / full_pairs
