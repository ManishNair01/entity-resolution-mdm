"""Phase 2: the check types compile to the right predicate, and the engine records what fires.

The rules themselves are the owner's (`config/dq_rules.yaml`); what is tested
here is the mechanism they are written against.
"""

from __future__ import annotations

import duckdb
import pytest

from src import dq_rules, ingest


def violations(check: dict, values: list, field: str = "v") -> list:
    """Return the values a check rejects, evaluated the way the engine evaluates it."""
    predicate = dq_rules.check_predicate(field, check)
    with duckdb.connect() as con:
        con.execute(f"CREATE TABLE t ({field} VARCHAR)")
        con.executemany(f"INSERT INTO t VALUES (?)", [(value,) for value in values])
        rows = con.execute(f"SELECT {field} FROM t WHERE NOT ({predicate})").fetchall()
    return [row[0] for row in rows]


# --- check types --------------------------------------------------------------


def test_not_null_is_the_only_check_that_fires_on_null():
    assert violations({"type": "not_null"}, [None, "", "a"]) == [None]
    for check in (
        {"type": "not_blank"},
        {"type": "in_set", "values": ["a"]},
        {"type": "matches_regex", "pattern": "^a$"},
        {"type": "length_between", "min": 1, "max": 1},
        {"type": "parses_as_date", "format": "%Y%m%d"},
    ):
        assert violations(check, [None]) == [], f"{check['type']} fired on NULL"


def test_not_blank_catches_whitespace_only():
    assert violations({"type": "not_blank"}, ["a", "", "   ", None]) == ["", "   "]


def test_in_set_ignores_case_and_surrounding_space_by_default():
    check = {"type": "in_set", "values": ["nsw", "vic"]}
    assert violations(check, ["nsw", "NSW", " vic ", "nws", None]) == ["nws"]


def test_in_set_can_be_made_case_sensitive():
    check = {"type": "in_set", "values": ["nsw"], "case_sensitive": True}
    assert violations(check, ["nsw", "NSW"]) == ["NSW"]


def test_in_set_survives_a_quote_in_a_value():
    """Config is data: a value with an apostrophe must not break the SQL."""
    check = {"type": "in_set", "values": ["o'brien"]}
    assert violations(check, ["o'brien", "smith"]) == ["smith"]


def test_matches_regex():
    check = {"type": "matches_regex", "pattern": "^[0-9]{4}$"}
    assert violations(check, ["1234", "12a4", "12345", None]) == ["12a4", "12345"]


def test_length_between():
    check = {"type": "length_between", "min": 4, "max": 4}
    assert violations(check, ["1234", "123", "12345", None]) == ["123", "12345"]


def test_parses_as_date_rejects_impossible_calendar_dates():
    check = {"type": "parses_as_date", "format": "%Y%m%d"}
    assert violations(check, ["19700101", "19320239", "1970-01-01", None]) == [
        "19320239",
        "1970-01-01",
    ]


def test_unknown_check_type_is_refused():
    with pytest.raises(ValueError, match="unknown check type"):
        dq_rules.check_predicate("v", {"type": "vibe_check"})


def test_missing_check_parameter_is_refused():
    with pytest.raises(ValueError, match="missing required key"):
        dq_rules.check_predicate("v", {"type": "matches_regex"})


def test_length_between_rejects_a_reversed_range():
    with pytest.raises(ValueError, match="greater than"):
        dq_rules.check_predicate("v", {"type": "length_between", "min": 9, "max": 1})


# --- rule validation ----------------------------------------------------------


def rule(**overrides) -> dict:
    base = {
        "id": "DQ-T-001",
        "field": "v",
        "dimension": "validity",
        "description": "test rule",
        "severity": "error",
        "check": {"type": "not_null"},
    }
    base.update(overrides)
    return base


def test_valid_rules_pass_validation():
    assert dq_rules.validate_rules({"rules": [rule()]}) == [rule()]


def test_empty_config_means_no_rules():
    assert dq_rules.validate_rules({}) == []
    assert dq_rules.validate_rules({"rules": None}) == []


@pytest.mark.parametrize("missing", dq_rules.REQUIRED_RULE_KEYS)
def test_a_rule_missing_any_required_key_is_refused(missing):
    incomplete = {key: value for key, value in rule().items() if key != missing}
    with pytest.raises(ValueError, match="missing"):
        dq_rules.validate_rules({"rules": [incomplete]})


def test_duplicate_rule_ids_are_refused():
    """Ids name the rule in metrics.json, so two rules cannot share one."""
    with pytest.raises(ValueError, match="duplicate rule id"):
        dq_rules.validate_rules({"rules": [rule(), rule(field="w")]})


def test_dimension_and_severity_are_constrained():
    with pytest.raises(ValueError, match="dimension"):
        dq_rules.validate_rules({"rules": [rule(dimension="vibes")]})
    with pytest.raises(ValueError, match="severity"):
        dq_rules.validate_rules({"rules": [rule(severity="catastrophic")]})


def test_a_bad_check_fails_validation_before_any_sql_runs():
    with pytest.raises(ValueError, match="unknown check type"):
        dq_rules.validate_rules({"rules": [rule(check={"type": "vibe_check"})]})


def test_missing_config_file_is_an_error_not_an_empty_config(tmp_path):
    with pytest.raises(FileNotFoundError):
        dq_rules.load_config(tmp_path / "absent.yaml")


def test_the_committed_config_is_loadable_and_valid():
    """Every committed rule must compile for the raw pass and the cleaned pass."""
    from src import standardize

    config = dq_rules.load_config()
    rules = dq_rules.validate_rules(config)
    assert rules, "the committed config holds no rules"

    raw_columns = {"surname", "date_of_birth", "postcode", "soc_sec_id", "state"}
    std_columns = raw_columns | {f"{c}_std" for c in raw_columns}
    for columns in (raw_columns, std_columns):
        for rule in rules:
            dq_rules.compile_rule(rule, columns)

    # Building the SELECT compiles every standardization chain.
    assert standardize.standardized_fields(config)
