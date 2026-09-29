"""Phase 2: each standardization transform, including the edge cases (null, empty, already clean).

Which transforms apply to which field is the owner's decision, in
`config/dq_rules.yaml`. These tests cover what each one does when it is used.
"""

from __future__ import annotations

import duckdb
import pytest

from src import ingest, standardize


def applied(steps: list[dict], values: list, field: str = "v") -> list:
    """Run a chain of steps over `values` the way the stage runs it."""
    expr = standardize.field_expr(field, steps)
    with duckdb.connect() as con:
        con.execute(f"CREATE TABLE t ({field} VARCHAR)")
        con.executemany(f"INSERT INTO t VALUES (?)", [(value,) for value in values])
        rows = con.execute(f"SELECT {expr} FROM t").fetchall()
    return [row[0] for row in rows]


# --- individual transforms ----------------------------------------------------


def test_trim_leaves_null_and_clean_values_alone():
    assert applied([{"type": "trim"}], ["  a  ", "a", "", "   ", None]) == ["a", "a", "", "", None]


def test_collapse_whitespace():
    assert applied(
        [{"type": "collapse_whitespace"}], ["a   b", "a b", "a\tb", None]
    ) == ["a b", "a b", "a b", None]


def test_lowercase():
    assert applied([{"type": "lowercase"}], ["NSW", "nsw", "", None]) == ["nsw", "nsw", "", None]


def test_strip_non_digits():
    assert applied(
        [{"type": "strip_non_digits"}], ["12-34 ", "1234", "abc", "", None]
    ) == ["1234", "1234", "", "", None]


def test_normalize_date_reformats_what_parses_and_keeps_what_does_not():
    step = {"type": "normalize_date", "from_format": "%Y%m%d", "to_format": "%Y-%m-%d"}
    assert applied([step], ["19700101", "19320239", "", None]) == [
        "1970-01-01",
        "19320239",
        "",
        None,
    ]


def test_normalize_date_can_null_unparseable_values_instead():
    step = {
        "type": "normalize_date",
        "from_format": "%Y%m%d",
        "to_format": "%Y-%m-%d",
        "on_error": "null",
    }
    assert applied([step], ["19700101", "19320239"]) == ["1970-01-01", None]


def test_normalize_date_refuses_an_unknown_on_error():
    with pytest.raises(ValueError, match="on_error"):
        standardize.field_expr(
            "v",
            [{"type": "normalize_date", "from_format": "%Y", "to_format": "%Y", "on_error": "shrug"}],
        )


def test_map_values_replaces_listed_values_only():
    step = {"type": "map_values", "mapping": {"nws": "nsw", "vci": "vic"}}
    assert applied([step], ["nws", "vci", "qld", "", None]) == ["nsw", "vic", "qld", "", None]


def test_replace_words_respects_word_boundaries():
    step = {"type": "replace_words", "mapping": {"vlge": "village", "st": "street"}}
    assert applied([step], ["brentwood vlge", "vlgee", "high st", "stone", None]) == [
        "brentwood village",
        "vlgee",
        "high street",
        "stone",
        None,
    ]


def test_a_quote_in_a_mapping_does_not_break_the_sql():
    step = {"type": "map_values", "mapping": {"o'brien": "obrien"}}
    assert applied([step], ["o'brien", "smith"]) == ["obrien", "smith"]


def test_steps_apply_in_the_order_written():
    """trim before map_values matches; the other way round it misses."""
    matching = [{"type": "trim"}, {"type": "map_values", "mapping": {"nws": "nsw"}}]
    reversed_order = [{"type": "map_values", "mapping": {"nws": "nsw"}}, {"type": "trim"}]
    assert applied(matching, [" nws "]) == ["nsw"]
    assert applied(reversed_order, [" nws "]) == ["nws"]


def test_unknown_transform_is_refused():
    with pytest.raises(ValueError, match="unknown standardization type"):
        standardize.field_expr("v", [{"type": "vibe"}])


def test_a_step_without_a_type_is_refused():
    with pytest.raises(ValueError, match="'type'"):
        standardize.field_expr("v", [{"mapping": {"a": "b"}}])


def test_a_field_standardized_twice_is_refused():
    config = {"standardization": [{"field": "state", "steps": []}, {"field": "state", "steps": []}]}
    with pytest.raises(ValueError, match="standardized twice"):
        standardize.standardized_fields(config)


def test_no_steps_means_the_value_is_carried_through_unchanged():
    assert standardize.standardized_fields({"standardization": [{"field": "state"}]}) == [
        ("state", "CAST(state AS VARCHAR)")
    ]


# --- the stage ----------------------------------------------------------------


def test_ground_truth_is_not_carried_into_the_table():
    """Hard rule 1: the label must not travel downstream, so it is not selected."""
    sql = standardize.select_sql([("state", "LOWER(state)")])
    for guarded in ("true_cluster_id", "rec_id"):
        assert guarded not in sql
        assert guarded not in standardize.CARRIED_COLUMNS


CONFIG_YAML = """
standardization:
  - field: state
    steps:
      - {type: trim}
      - {type: lowercase}
      - {type: map_values, mapping: {nws: nsw}}
  - field: soc_sec_id
    steps:
      - {type: strip_non_digits}
"""


@pytest.fixture()
def source_db(tmp_path, monkeypatch):
    """A `raw_customers` table with every carried column, two rows, and a temp config."""
    monkeypatch.setattr(ingest, "METRICS_PATH", tmp_path / "metrics.json")
    config_path = tmp_path / "dq_rules.yaml"
    config_path.write_text(CONFIG_YAML, encoding="utf-8")

    columns = ", ".join(
        "CAST(NULL AS VARCHAR) AS " + column
        for column in standardize.CARRIED_COLUMNS
        if column not in ("unique_id", "state", "soc_sec_id", "last_updated")
    )
    db_path = tmp_path / "unit.duckdb"
    with duckdb.connect(str(db_path)) as con:
        con.execute(
            f"""
            CREATE TABLE raw_customers AS
            SELECT
                unique_id,
                state,
                soc_sec_id,
                CAST('2026-01-01' AS DATE) AS last_updated,
                {columns}
            FROM (VALUES (1, ' NWS ', '12-34'), (2, 'vic', '5678')) AS t(unique_id, state, soc_sec_id)
            """
        )
    return db_path, config_path


def test_run_writes_std_columns_beside_the_originals(source_db):
    db_path, config_path = source_db
    metrics = standardize.run(db_path, config_path)

    assert metrics["standardize.row_count"] == 2
    assert metrics["standardize.standardized_field_count"] == 2
    # Row 1 changes in both fields; row 2's state and id are already clean.
    assert metrics["standardize.changed_by_field"] == {"state": 1, "soc_sec_id": 1}

    with duckdb.connect(str(db_path), read_only=True) as con:
        rows = con.execute(
            "SELECT state, state_std, soc_sec_id, soc_sec_id_std "
            "FROM std_customers ORDER BY unique_id"
        ).fetchall()
    assert rows == [(" NWS ", "nsw", "12-34", "1234"), ("vic", "vic", "5678", "5678")]


def test_run_does_not_touch_the_source_table(source_db):
    db_path, config_path = source_db
    with duckdb.connect(str(db_path), read_only=True) as con:
        before = con.execute("SELECT * FROM raw_customers ORDER BY unique_id").fetchall()

    standardize.run(db_path, config_path)

    with duckdb.connect(str(db_path), read_only=True) as con:
        after = con.execute("SELECT * FROM raw_customers ORDER BY unique_id").fetchall()
    assert before == after


def test_an_empty_config_still_produces_the_table(source_db):
    db_path, config_path = source_db
    config_path.write_text("standardization: []\n", encoding="utf-8")
    metrics = standardize.run(db_path, config_path)

    assert metrics["standardize.standardized_field_count"] == 0
    with duckdb.connect(str(db_path), read_only=True) as con:
        columns = {row[0] for row in con.execute("DESCRIBE std_customers").fetchall()}
    assert columns == set(standardize.CARRIED_COLUMNS)
