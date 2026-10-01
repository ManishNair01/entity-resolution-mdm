"""Phase 2: the mechanisms the owner's `config/dq_rules.yaml` is written against.

Covers the check and transform types added for the approved policy (`present`,
`minimum_identity_evidence`, `replace_phrases`, `replace_contextual_word`), the
date-format switch between the raw and cleaned pass, and the age-review stage.
Cases are small hand-built values, not the owner's thresholds.
"""

from __future__ import annotations

import json

import duckdb
import pytest
import yaml

from src import age_review, dq_rules, ingest, standardize


def applied(steps, values):
    expr = standardize.field_expr("v", steps)
    with duckdb.connect() as con:
        con.execute("CREATE TABLE t (i INTEGER, v VARCHAR)")
        con.executemany("INSERT INTO t VALUES (?, ?)", list(enumerate(values)))
        return [row[0] for row in con.execute(f"SELECT {expr} FROM t ORDER BY i").fetchall()]


# --- present ------------------------------------------------------------------


def test_present_fails_on_null_and_blank_only():
    predicate = dq_rules.check_predicate("v", {"type": "present"})
    with duckdb.connect() as con:
        con.execute("CREATE TABLE t (v VARCHAR)")
        con.executemany("INSERT INTO t VALUES (?)", [(None,), ("",), ("  ",), ("a",), ("0",)])
        rejected = [r[0] for r in con.execute(f"SELECT v FROM t WHERE NOT ({predicate})").fetchall()]
    assert rejected == [None, "", "  "]


# --- date format switch -------------------------------------------------------


def test_for_column_swaps_in_the_standardized_format_only_for_std_columns():
    spec = {"type": "parses_as_date", "format": "%Y%m%d", "standardized_format": "%Y-%m-%d"}
    assert dq_rules.for_column(spec, standardized=False)["format"] == "%Y%m%d"
    assert dq_rules.for_column(spec, standardized=True)["format"] == "%Y-%m-%d"
    plain = {"type": "not_null"}
    assert dq_rules.for_column(plain, standardized=True) == plain


def test_a_date_rule_reads_the_raw_format_on_raw_and_iso_on_std():
    rule = {
        "id": "DQ-V-T",
        "field": "dob",
        "dimension": "validity",
        "description": "t",
        "severity": "error",
        "check": {
            "type": "parses_as_date",
            "format": "%Y%m%d",
            "standardized_format": "%Y-%m-%d",
        },
    }
    with duckdb.connect() as con:
        con.execute("CREATE TABLE t (dob VARCHAR, dob_std VARCHAR)")
        con.execute("INSERT INTO t VALUES ('19700101', '1970-01-01')")
        for columns, expected_field in (({"dob"}, "dob"), ({"dob", "dob_std"}, "dob_std")):
            field, predicate, _ = dq_rules.compile_rule(rule, columns)
            assert field == expected_field
            assert con.execute(f"SELECT {predicate} FROM t").fetchone()[0] is True


# --- minimum_identity_evidence ------------------------------------------------

EVIDENCE = {
    "type": "minimum_identity_evidence",
    "minimum_signals": 3,
    "max_substitutes": 1,
    "primary": [
        {"field": "surname", "usable_when": {"type": "present"}},
        {"field": "dob", "usable_when": {"type": "parses_as_date", "format": "%Y%m%d"}},
        {"field": "postcode", "usable_when": {"type": "matches_regex", "pattern": "^[0-9]{4}$"}},
    ],
    "substitutes": [
        {"field": "ssid", "usable_when": {"type": "matches_regex", "pattern": "^[0-9]{7}$"}},
    ],
}


def failing_evidence(rows):
    rule = {
        "id": "DQ-C-T",
        "field": "identity_evidence",
        "dimension": "completeness",
        "description": "t",
        "severity": "error",
        "check": EVIDENCE,
    }
    _, predicate, value = dq_rules.compile_rule(rule, {"surname", "dob", "postcode", "ssid"})
    with duckdb.connect() as con:
        con.execute("CREATE TABLE t (i INTEGER, surname VARCHAR, dob VARCHAR, postcode VARCHAR, ssid VARCHAR)")
        con.executemany("INSERT INTO t VALUES (?, ?, ?, ?, ?)", [(i, *row) for i, row in enumerate(rows)])
        return con.execute(f"SELECT i, {value} FROM t WHERE NOT ({predicate}) ORDER BY i").fetchall()


def test_three_usable_primary_signals_pass_with_or_without_an_identifier():
    assert failing_evidence([("smith", "19700101", "2000", None), ("smith", "19700101", "2000", "1234567")]) == []


def test_soc_sec_id_replaces_one_unusable_primary_signal():
    rows = [
        (None, "19700101", "2000", "1234567"),  # surname missing
        ("smith", "19700230", "2000", "1234567"),  # DOB impossible, so unavailable
        ("smith", "19700101", "20A0", "1234567"),  # postcode malformed
    ]
    assert failing_evidence(rows) == []


def test_soc_sec_id_cannot_replace_two_primary_signals():
    rows = [(None, None, "2000", "1234567"), ("smith", "19700230", "20A0", "1234567")]
    assert failing_evidence(rows) == [(0, "usable_signals=2"), (1, "usable_signals=2")]


def test_an_invalid_identifier_supplies_no_signal():
    assert failing_evidence([(None, "19700101", "2000", "12-34567")]) == [(0, "usable_signals=2")]


def test_the_substitute_cap_is_enforced():
    """With max_substitutes 0 an identifier substitutes for nothing."""
    check = {**EVIDENCE, "max_substitutes": 0}
    _, predicate, _ = dq_rules.compile_rule(
        {"field": "identity_evidence", "check": check}, {"surname", "dob", "postcode", "ssid"}
    )
    with duckdb.connect() as con:
        con.execute("CREATE TABLE t (surname VARCHAR, dob VARCHAR, postcode VARCHAR, ssid VARCHAR)")
        con.execute("INSERT INTO t VALUES (NULL, '19700101', '2000', '1234567')")
        assert con.execute(f"SELECT {predicate} FROM t").fetchone()[0] is False


def test_evidence_check_needs_primary_signals():
    with pytest.raises(ValueError, match="primary"):
        dq_rules.compile_rule(
            {"field": "x", "check": {"type": "minimum_identity_evidence", "minimum_signals": 3}}
        )


def test_evidence_rule_reads_std_columns_when_they_exist():
    rule = {"field": "identity_evidence", "check": EVIDENCE}
    with duckdb.connect() as con:
        con.execute(
            "CREATE TABLE t (surname VARCHAR, dob VARCHAR, postcode VARCHAR, ssid VARCHAR, dob_std VARCHAR)"
        )
        # Raw DOB is impossible; the cleaned column has already nulled it.
        con.execute("INSERT INTO t VALUES ('smith', '19700230', '2000', NULL, NULL)")
        _, predicate, _ = dq_rules.compile_rule(rule, {"surname", "dob", "postcode", "ssid", "dob_std"})
        assert con.execute(f"SELECT {predicate} FROM t").fetchone()[0] is False


# --- standardization transforms ----------------------------------------------


def test_normalize_date_reads_an_unquoted_yaml_null_as_null():
    step = yaml.safe_load("{type: normalize_date, from_format: '%Y%m%d', to_format: '%Y-%m-%d', on_error: null}")
    assert step["on_error"] is None
    assert applied([step], ["19700101", "19700230"]) == ["1970-01-01", None]


def test_replace_phrases_joins_a_split_word_and_only_as_a_phrase():
    step = {"type": "replace_phrases", "mapping": {"st reet": "street"}}
    assert applied([step], ["1 main st reet", "west reet", "st reeting", None]) == [
        "1 main street",
        "west reet",
        "st reeting",
        None,
    ]


def test_replace_contextual_word_is_saint_at_the_start_and_street_elsewhere():
    step = {"type": "replace_contextual_word", "word": "st", "at_start": "saint", "otherwise": "street"}
    assert applied([step], ["st kilda rd", "high st", "st st", "stone st", "east", "", None]) == [
        "saint kilda rd",
        "high street",
        "saint street",
        "stone street",
        "east",
        "",
        None,
    ]


def test_the_address_chain_from_the_config_gives_the_approved_expansions():
    config = yaml.safe_load((dq_rules.CONFIG_PATH).read_text(encoding="utf-8"))
    steps = next(e["steps"] for e in config["standardization"] if e["field"] == "address_1")
    assert applied(
        steps,
        ["  St  Kilda  ", "12 main st reet", "mt eliza vlge", "hse 3 flr 2 unt 1", "Castle st"],
    ) == ["saint kilda", "12 main street", "mount eliza village", "house 3 floor 2 unit 1", "castle street"]


def committed_steps(field):
    config = yaml.safe_load(dq_rules.CONFIG_PATH.read_text(encoding="utf-8"))
    return next(e["steps"] for e in config["standardization"] if e["field"] == field)


def test_the_committed_name_and_address_chains_remove_padding_of_every_kind():
    assert applied(committed_steps("given_name"), ["\t MARY \n", " Ann Marie ", "Jo  Anne"]) == [
        "mary",
        "ann marie",
        "jo anne",
    ]
    assert applied(committed_steps("address_1"), ["\tSt  Kilda\n", " main\tst "]) == [
        "saint kilda",
        "main street",
    ]


def test_the_committed_identifier_and_date_chains_trim_then_validate_strictly():
    assert applied(committed_steps("postcode"), ["\t2000\n", " 2000 ", "20 00"]) == ["2000", "2000", "20 00"]
    assert applied(committed_steps("date_of_birth"), ["19700101", "1970011", " 19700101", "19700230", "\t19700101\n", "1970 0101", None, " "]) == [
        "1970-01-01",
        None,
        "1970-01-01",
        None,
        "1970-01-01",
        None,
        None,
        None,
    ]


# --- committed config end to end ---------------------------------------------


def test_every_state_mapping_in_the_config_lands_on_an_accepted_code():
    """The mapped codes must satisfy DQ-V-004, or the cleaned pass would still flag them."""
    config = yaml.safe_load(dq_rules.CONFIG_PATH.read_text(encoding="utf-8"))
    accepted = set(next(r for r in config["rules"] if r["id"] == "DQ-V-004")["check"]["values"])
    mapping = next(
        s for e in config["standardization"] if e["field"] == "state" for s in e["steps"]
        if s["type"] == "map_values"
    )["mapping"]
    assert set(mapping.values()) <= accepted
    assert not set(mapping) & accepted, "a mapping key is already an accepted code"


# --- age review ---------------------------------------------------------------

AGE_CONFIG = """
age_review:
  source_field: date_of_birth
  standardized_field: date_of_birth_std
  reference_date: "2026-09-22"
  output_table: age_review
  initial_status: pending
  bands:
    - {reason: minor_verification, minimum_age: 0, maximum_age: 17}
    - {reason: age_100_plus, minimum_age: 100}
"""


@pytest.fixture()
def std_db(tmp_path, monkeypatch):
    monkeypatch.setattr(ingest, "METRICS_PATH", tmp_path / "metrics.json")
    config_path = tmp_path / "dq_rules.yaml"
    config_path.write_text(AGE_CONFIG, encoding="utf-8")
    db_path = tmp_path / "unit.duckdb"
    rows = [
        (1, "2009-09-22"),  # turns 17 on the reference date
        (2, "2008-09-22"),  # turns 18 on the reference date: not a minor
        (3, "2008-09-23"),  # one day short of 18: still 17
        (4, "1926-09-22"),  # turns 100 on the reference date
        (5, "1926-09-23"),  # 99
        (6, "1900-01-01"),
        (7, None),  # missing or impossible DOB was nulled by standardization
        (8, "1990-05-05"),
    ]
    with duckdb.connect(str(db_path)) as con:
        con.execute("CREATE TABLE std_customers (unique_id BIGINT, date_of_birth_std VARCHAR)")
        con.executemany("INSERT INTO std_customers VALUES (?, ?)", rows)
    return db_path, config_path


def test_age_is_completed_years_on_the_fixed_reference_date(std_db):
    db_path, config_path = std_db
    age_review.run(db_path, config_path)
    with duckdb.connect(str(db_path), read_only=True) as con:
        rows = con.execute(
            "SELECT unique_id, calculated_age, reason FROM age_review ORDER BY unique_id"
        ).fetchall()
    assert rows == [
        (1, 17, "minor_verification"),
        (3, 17, "minor_verification"),
        (4, 100, "age_100_plus"),
        (6, 126, "age_100_plus"),
    ]


def test_review_rows_reference_the_customer_and_start_pending(std_db):
    db_path, config_path = std_db
    age_review.run(db_path, config_path)
    with duckdb.connect(str(db_path), read_only=True) as con:
        columns = [c[0] for c in con.execute("SELECT * FROM age_review").description]
        statuses = {r[0] for r in con.execute("SELECT status FROM age_review").fetchall()}
        dates = {str(r[0]) for r in con.execute("SELECT calculation_date FROM age_review").fetchall()}
    assert columns == ["unique_id", "calculated_age", "calculation_date", "reason", "status"]
    assert statuses == {"pending"}
    assert dates == {"2026-09-22"}


def test_age_review_metrics_report_zero_for_an_empty_band(std_db):
    db_path, config_path = std_db
    with duckdb.connect(str(db_path)) as con:
        con.execute("DELETE FROM std_customers WHERE unique_id IN (4, 6)")
    metrics = age_review.run(db_path, config_path)
    assert metrics["age_review.flagged_by_reason"] == {"minor_verification": 2, "age_100_plus": 0}
    assert metrics["age_review.flagged_count"] == 2


def test_age_review_is_repeatable_and_leaves_std_customers_alone(std_db):
    db_path, config_path = std_db
    with duckdb.connect(str(db_path), read_only=True) as con:
        before = con.execute("SELECT * FROM std_customers ORDER BY unique_id").fetchall()
    first = age_review.run(db_path, config_path)
    second = age_review.run(db_path, config_path)
    with duckdb.connect(str(db_path), read_only=True) as con:
        after = con.execute("SELECT * FROM std_customers ORDER BY unique_id").fetchall()
    assert first == second
    assert before == after


def test_no_age_review_section_is_a_no_op(std_db):
    db_path, config_path = std_db
    config_path.write_text("rules: []\n", encoding="utf-8")
    assert age_review.run(db_path, config_path) == {}


# --- output protection and stale outputs --------------------------------------

OTHER_STAGE_TABLES = ("raw_customers", "dq_violations_raw", "dq_violations_std")


def tables(db_path):
    with duckdb.connect(str(db_path), read_only=True) as con:
        return {row[0] for row in con.execute("SHOW TABLES").fetchall()}


def snapshot(db_path, names):
    with duckdb.connect(str(db_path), read_only=True) as con:
        return {n: con.execute(f"SELECT * FROM {n} ORDER BY ALL").fetchall() for n in names}


def use_output_table(config_path, name):
    config_path.write_text(
        AGE_CONFIG.replace("output_table: age_review", f"output_table: {name}"), encoding="utf-8"
    )


def add_other_stage_tables(db_path):
    with duckdb.connect(str(db_path)) as con:
        for name in OTHER_STAGE_TABLES:
            con.execute(f"CREATE TABLE {name} AS SELECT 1 AS unique_id, 'keep me' AS payload")


@pytest.mark.parametrize("name", ["raw_customers", "std_customers", "dq_violations_raw", "dq_violations_std"])
def test_an_output_name_owned_by_another_stage_is_refused_and_nothing_is_overwritten(std_db, name):
    """`CREATE OR REPLACE` under a configured name used to wipe `raw_customers`."""
    db_path, config_path = std_db
    add_other_stage_tables(db_path)
    watched = ("std_customers", *OTHER_STAGE_TABLES)
    before = snapshot(db_path, watched)

    use_output_table(config_path, name)
    with pytest.raises(ValueError, match="another stage"):
        age_review.run(db_path, config_path)

    assert snapshot(db_path, watched) == before


def test_an_existing_table_that_is_not_an_age_review_output_is_never_replaced(std_db):
    """The name is not reserved, but the table is somebody else's: say so, don't replace it."""
    db_path, config_path = std_db
    with duckdb.connect(str(db_path)) as con:
        con.execute("CREATE TABLE clusters AS SELECT 1 AS unique_id, 7 AS cluster_id")
    before = snapshot(db_path, ["clusters"])

    use_output_table(config_path, "clusters")
    with pytest.raises(ValueError, match="not an age-review output"):
        age_review.run(db_path, config_path)

    assert snapshot(db_path, ["clusters"]) == before


def test_disabling_age_review_removes_its_table_and_its_metrics_but_not_others(std_db):
    db_path, config_path = std_db
    ingest.write_metrics({"dq.raw.rule_count": 3})
    age_review.run(db_path, config_path)
    assert "age_review" in tables(db_path)
    assert any(k.startswith("age_review.") for k in json.loads(ingest.METRICS_PATH.read_text()))

    config_path.write_text("rules: []\n", encoding="utf-8")
    assert age_review.run(db_path, config_path) == {}

    assert "age_review" not in tables(db_path)
    assert "std_customers" in tables(db_path)
    assert json.loads(ingest.METRICS_PATH.read_text()) == {"dq.raw.rule_count": 3}


def test_renaming_the_output_table_drops_the_old_one(std_db):
    db_path, config_path = std_db
    age_review.run(db_path, config_path)

    use_output_table(config_path, "age_flags")
    metrics = age_review.run(db_path, config_path)

    assert {"age_flags", "std_customers"} <= tables(db_path)
    assert "age_review" not in tables(db_path)
    assert metrics["age_review.output_table"] == "age_flags"


def test_a_hand_edited_metrics_file_cannot_point_cleanup_at_another_table(std_db):
    """Cleanup trusts a recorded table name only if the table has this stage's own columns."""
    db_path, config_path = std_db
    add_other_stage_tables(db_path)
    watched = ("std_customers", *OTHER_STAGE_TABLES)
    before = snapshot(db_path, watched)

    for tampered in ("std_customers", "raw_customers", "x; DROP TABLE std_customers"):
        ingest.write_metrics({age_review.OUTPUT_TABLE_METRIC: tampered})
        config_path.write_text("rules: []\n", encoding="utf-8")
        age_review.run(db_path, config_path)

    assert snapshot(db_path, watched) == before


def test_a_switched_off_stage_does_not_create_a_database_file(tmp_path, monkeypatch):
    monkeypatch.setattr(ingest, "METRICS_PATH", tmp_path / "metrics.json")
    config_path = tmp_path / "dq_rules.yaml"
    config_path.write_text("rules: []\n", encoding="utf-8")
    db_path = tmp_path / "absent.duckdb"

    assert age_review.run(db_path, config_path) == {}
    assert not db_path.exists()


def test_remove_metrics_returns_what_it_removed_and_keeps_the_rest(tmp_path):
    path = tmp_path / "metrics.json"
    assert ingest.remove_metrics("a.", path) == {}
    assert not path.exists()

    ingest.write_metrics({"a.x": 1, "a.y": 2, "b.z": 3}, path)
    assert ingest.remove_metrics("a.", path) == {"a.x": 1, "a.y": 2}
    assert json.loads(path.read_text(encoding="utf-8")) == {"b.z": 3}


@pytest.mark.parametrize(
    "bad",
    [
        {"reference_date": "22/09/2026"},
        {"output_table": "age review; drop table x"},
        {"bands": []},
        {"bands": [{"reason": "r"}]},
        {"bands": [{"reason": "r", "minimum_age": 5, "maximum_age": 1}]},
        {"bands": [{"reason": "r", "minimum_age": 1}, {"reason": "r", "minimum_age": 2}]},
    ],
)
def test_a_bad_age_review_section_is_refused(bad):
    section = yaml.safe_load(AGE_CONFIG)["age_review"] | bad
    with pytest.raises(ValueError):
        age_review.validate_config(section)
