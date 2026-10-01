"""Phase 3: the pair-generation mechanism behind the baseline matcher and the blocking rules.

The rules themselves are the owner's (`config/baseline.yaml`, `config/blocking.yaml`);
these tests cover what the engine does with whatever rules it is given, on small
hand-built tables, plus an independent cross-check of the pair counts against Splink.
Scoring against ground truth is `evaluate.py`'s job and is not tested here.
"""

from __future__ import annotations

import json
import random

import duckdb
import pytest
import yaml

from src import baseline, blocking, dq_rules, ingest, pairs, standardize

# Seven records built to hit every edge: shared values, a NULL, an empty string,
# and two records that are blank in every field.
ROWS = [
    (1, "smith", "1970-01-01", "2000", "mary"),
    (2, "smith", "1970-01-01", "2000", "mark"),
    (3, "smith", "1980-05-05", "2000", None),
    (4, "jones", None, None, "mary"),
    (5, "jones", None, "", "mary"),
    (6, "", "", None, ""),
    (7, "", "", None, ""),
]
SURNAME = {"id": "surname", "description": "d", "keys": ["surname_std"]}
DOB = {"id": "date_of_birth", "description": "d", "keys": ["date_of_birth_std"]}
POSTCODE_INITIAL = {
    "id": "postcode_given_initial",
    "description": "d",
    "keys": ["postcode_std", {"field": "given_name_std", "prefix": 1}],
}
BLOCKING = {"rules": [SURNAME, DOB, POSTCODE_INITIAL]}
BASELINE = {
    "variants": [
        {
            "id": "surname_dob_postcode",
            "description": "d",
            "match_on": ["surname_std", "date_of_birth_std", "postcode_std"],
        }
    ]
}


def write_config(tmp_path, name, data):
    path = tmp_path / name
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    return path


def make_db(path, rows=ROWS):
    with duckdb.connect(str(path)) as con:
        con.execute(
            "CREATE TABLE std_customers (unique_id BIGINT, surname_std VARCHAR, "
            "date_of_birth_std VARCHAR, postcode_std VARCHAR, given_name_std VARCHAR)"
        )
        con.executemany("INSERT INTO std_customers VALUES (?, ?, ?, ?, ?)", rows)
        con.execute(
            "CREATE TABLE dq_violations_std (unique_id BIGINT, rule_id VARCHAR, "
            "field VARCHAR, dimension VARCHAR, severity VARCHAR, value VARCHAR)"
        )
    return path


@pytest.fixture()
def db(tmp_path, monkeypatch):
    monkeypatch.setattr(ingest, "METRICS_PATH", tmp_path / "metrics.json")
    return make_db(tmp_path / "unit.duckdb")


def pairs_of(db_path, table):
    with duckdb.connect(str(db_path), read_only=True) as con:
        return con.execute(f"SELECT unique_id_l, unique_id_r FROM {table}").fetchall()


def tables(db_path):
    with duckdb.connect(str(db_path), read_only=True) as con:
        return {row[0] for row in con.execute("SHOW TABLES").fetchall()}


def metrics():
    return json.loads(ingest.METRICS_PATH.read_text(encoding="utf-8"))


def select_pairs(keys, rows=ROWS):
    with duckdb.connect() as con:
        con.execute(
            "CREATE TABLE t (unique_id BIGINT, surname_std VARCHAR, date_of_birth_std VARCHAR, "
            "postcode_std VARCHAR, given_name_std VARCHAR)"
        )
        con.executemany("INSERT INTO t VALUES (?, ?, ?, ?, ?)", rows)
        return con.execute(pairs.pairs_select("t", keys)).fetchall()


# --- pair generation ----------------------------------------------------------


def test_pairs_are_canonical_unique_sorted_and_never_self_pairs():
    found = select_pairs([("surname_std", None)])
    assert found == [(1, 2), (1, 3), (2, 3), (4, 5)]
    assert all(left < right for left, right in found)
    assert len(set(found)) == len(found)
    assert found == sorted(found)


def test_missing_and_blank_values_never_match_each_other():
    """Records 6 and 7 are blank in every field; record 4 and 5 differ only by NULL vs ''."""
    assert (6, 7) not in select_pairs([("surname_std", None)])
    assert select_pairs([("date_of_birth_std", None)]) == [(1, 2)]
    assert select_pairs([("postcode_std", None)]) == [(1, 2), (1, 3), (2, 3)]


def test_a_prefix_key_compares_only_the_leading_characters():
    assert select_pairs([("given_name_std", 2)]) == [(1, 2), (1, 4), (1, 5), (2, 4), (2, 5), (4, 5)]
    assert select_pairs([("given_name_std", 1)]) == select_pairs([("given_name_std", 2)])
    assert select_pairs([("given_name_std", 4)]) == [(1, 4), (1, 5), (4, 5)]


def test_every_key_must_agree():
    both = select_pairs([("postcode_std", None), ("given_name_std", 1)])
    assert both == [(1, 2)]


def test_full_pair_count_and_reduction_ratio():
    assert [pairs.full_pair_count(n) for n in (0, 1, 2, 7)] == [0, 0, 1, 21]
    assert pairs.reduction_ratio(1, 4) == 0.75
    assert pairs.reduction_ratio(0, 4) == 1.0
    assert pairs.reduction_ratio(0, 0) is None


def test_pair_counts_agree_with_splinks_independent_count():
    """Cross-check: Splink counts the same deduplicated pairs by its own route."""
    from splink import DuckDBAPI
    from splink.blocking_analysis import count_comparisons_from_blocking_rule

    rng = random.Random(7)
    pick = lambda pool: rng.choice(pool + [None])
    rows = [
        (i, pick(["a", "b", "c"]), pick(["d1", "d2"]), pick(["p1", "p2", "p3"]), pick(["mary", "mark", "ann"]))
        for i in range(80)
    ]
    splink_rules = {
        "surname": "l.surname_std = r.surname_std",
        "date_of_birth": "l.date_of_birth_std = r.date_of_birth_std",
        "postcode_given_initial": (
            "l.postcode_std = r.postcode_std AND LEFT(l.given_name_std, 1) = LEFT(r.given_name_std, 1)"
        ),
    }
    with duckdb.connect() as con:
        con.execute(
            "CREATE TABLE t (unique_id BIGINT, surname_std VARCHAR, date_of_birth_std VARCHAR, "
            "postcode_std VARCHAR, given_name_std VARCHAR)"
        )
        con.executemany("INSERT INTO t VALUES (?, ?, ?, ?, ?)", rows)
        frame = con.execute("SELECT * FROM t").fetch_df()
    for rule in BLOCKING["rules"]:
        mine = len(select_pairs(pairs.parse_keys(rule["keys"]), rows))
        theirs = count_comparisons_from_blocking_rule(
            table_or_tables=frame,
            blocking_rule=splink_rules[rule["id"]],
            link_type="dedupe_only",
            db_api=DuckDBAPI(),
        )["number_of_comparisons_to_be_scored_post_filter_conditions"]
        assert mine == theirs, rule["id"]


# --- the stages ---------------------------------------------------------------


def test_blocking_writes_a_pair_table_per_rule_and_the_union(db, tmp_path):
    config = write_config(tmp_path, "blocking.yaml", BLOCKING)
    result = blocking.run(db, config)

    assert pairs_of(db, "blocking_pairs_surname") == [(1, 2), (1, 3), (2, 3), (4, 5)]
    assert pairs_of(db, "blocking_pairs_date_of_birth") == [(1, 2)]
    assert pairs_of(db, "blocking_pairs_postcode_given_initial") == [(1, 2)]
    # (1, 2) comes from all three rules and must appear once in the union.
    assert pairs_of(db, "blocking_pairs_union") == [(1, 2), (1, 3), (2, 3), (4, 5)]

    assert all(metrics()[key] == value for key, value in result.items())  # all written to the file
    assert result["blocking.record_count"] == 7
    assert result["blocking.full_pair_count"] == 21
    assert result["blocking.rule_count"] == 3
    assert result["blocking.candidate_pairs_by_rule"] == {
        "surname": 4,
        "date_of_birth": 1,
        "postcode_given_initial": 1,
    }
    assert result["blocking.union_candidate_pairs"] == 4
    assert result["blocking.reduction_ratio_by_rule"]["surname"] == 1 - 4 / 21
    assert result["blocking.union_reduction_ratio"] == 1 - 4 / 21


def test_baseline_writes_one_pair_table_per_variant(db, tmp_path):
    config = write_config(tmp_path, "baseline.yaml", BASELINE)
    result = baseline.run(db, config)

    assert pairs_of(db, "baseline_pairs_surname_dob_postcode") == [(1, 2)]
    assert result == {
        "baseline.variant_count": 1,
        "baseline.matched_pairs_by_variant": {"surname_dob_postcode": 1},
    }


def test_every_output_has_exactly_the_pair_columns(db, tmp_path):
    baseline.run(db, write_config(tmp_path, "baseline.yaml", BASELINE))
    blocking.run(db, write_config(tmp_path, "blocking.yaml", BLOCKING))
    with duckdb.connect(str(db), read_only=True) as con:
        for table in tables(db) - {"std_customers", "dq_violations_std"}:
            assert [c[0] for c in con.execute(f"SELECT * FROM {table}").description] == [
                "unique_id_l",
                "unique_id_r",
            ], table


def test_a_variant_that_matches_nothing_is_reported_as_zero(db, tmp_path):
    never = {"variants": [{"id": "never", "description": "d", "match_on": ["surname_std", "postcode_std", "date_of_birth_std", "given_name_std"]}]}
    # Records 1 and 2 differ on given name, so nothing agrees on all four.
    assert baseline.run(db, write_config(tmp_path, "b.yaml", never))["baseline.matched_pairs_by_variant"] == {"never": 0}
    assert pairs_of(db, "baseline_pairs_never") == []


def test_no_rules_gives_an_empty_union_and_zero_counts(db, tmp_path):
    result = blocking.run(db, write_config(tmp_path, "blocking.yaml", {"rules": []}))
    assert pairs_of(db, "blocking_pairs_union") == []
    assert result["blocking.rule_count"] == 0
    assert result["blocking.union_candidate_pairs"] == 0
    assert result["blocking.union_reduction_ratio"] == 1.0


def test_the_stages_are_repeatable_and_leave_their_inputs_alone(db, tmp_path):
    base_config = write_config(tmp_path, "baseline.yaml", BASELINE)
    block_config = write_config(tmp_path, "blocking.yaml", BLOCKING)
    with duckdb.connect(str(db), read_only=True) as con:
        before = con.execute("SELECT * FROM std_customers ORDER BY unique_id").fetchall()

    first = (baseline.run(db, base_config), blocking.run(db, block_config))
    snapshot = {t: pairs_of(db, t) for t in sorted(tables(db)) if t.endswith(("union", "surname"))}
    second = (baseline.run(db, base_config), blocking.run(db, block_config))

    assert first == second
    assert snapshot == {t: pairs_of(db, t) for t in sorted(tables(db)) if t.endswith(("union", "surname"))}
    with duckdb.connect(str(db), read_only=True) as con:
        assert con.execute("SELECT * FROM std_customers ORDER BY unique_id").fetchall() == before


# --- stale output -------------------------------------------------------------


def test_a_removed_or_renamed_rule_leaves_no_table_or_metric_behind(db, tmp_path):
    blocking.run(db, write_config(tmp_path, "blocking.yaml", BLOCKING))
    assert "blocking_pairs_date_of_birth" in tables(db)

    renamed = {"rules": [{**SURNAME, "id": "family_name"}]}
    blocking.run(db, write_config(tmp_path, "blocking.yaml", renamed))

    assert tables(db) == {
        "std_customers",
        "dq_violations_std",
        "blocking_pairs_family_name",
        "blocking_pairs_union",
    }
    assert set(metrics()["blocking.candidate_pairs_by_rule"]) == {"family_name"}


def test_each_stage_only_clears_its_own_prefix(db, tmp_path):
    blocking.run(db, write_config(tmp_path, "blocking.yaml", BLOCKING))
    baseline.run(db, write_config(tmp_path, "baseline.yaml", BASELINE))
    baseline.run(db, write_config(tmp_path, "baseline.yaml", {"variants": []}))

    assert "blocking_pairs_surname" in tables(db)
    assert "baseline_pairs_surname_dob_postcode" not in tables(db)
    assert "blocking.union_candidate_pairs" in metrics()
    assert metrics()["baseline.matched_pairs_by_variant"] == {}


def test_a_config_error_leaves_the_previous_output_untouched(db, tmp_path):
    good = write_config(tmp_path, "blocking.yaml", BLOCKING)
    blocking.run(db, good)
    before = {t: pairs_of(db, t) for t in tables(db) if t.startswith("blocking_pairs_")}
    saved = metrics()

    with pytest.raises(ValueError, match="duplicate id"):
        blocking.run(db, write_config(tmp_path, "bad.yaml", {"rules": [SURNAME, SURNAME]}))

    assert {t: pairs_of(db, t) for t in tables(db) if t.startswith("blocking_pairs_")} == before
    assert metrics() == saved


# --- values flagged invalid ---------------------------------------------------


def flag(db_path, field, dimension="validity"):
    with duckdb.connect(str(db_path)) as con:
        con.execute(
            "INSERT INTO dq_violations_std VALUES (1, 'DQ-V-T', ?, ?, 'error', '20A0')",
            [field, dimension],
        )


def test_a_present_value_flagged_invalid_stops_the_stage(db, tmp_path):
    """A flag alone must not become a valid join key."""
    baseline_config = write_config(tmp_path, "baseline.yaml", BASELINE)
    baseline.run(db, baseline_config)
    saved = metrics()

    flag(db, "postcode_std")
    with pytest.raises(ValueError, match="flagged invalid"):
        baseline.run(db, baseline_config)
    with pytest.raises(ValueError, match="postcode_std: 1"):
        blocking.run(db, write_config(tmp_path, "blocking.yaml", BLOCKING))

    # The refusal happens before anything is replaced.
    assert "baseline_pairs_surname_dob_postcode" in tables(db)
    assert metrics() == saved


def test_flags_that_do_not_touch_a_column_the_rules_read_are_fine(db, tmp_path):
    flag(db, "state_std")  # validity, but no rule reads state
    flag(db, "postcode_std", dimension="completeness")  # missing, not invalid
    baseline.run(db, write_config(tmp_path, "baseline.yaml", BASELINE))


def test_the_stage_needs_the_dq_violations_table(db, tmp_path):
    with duckdb.connect(str(db)) as con:
        con.execute("DROP TABLE dq_violations_std")
    with pytest.raises(ValueError, match="dq_std"):
        baseline.run(db, write_config(tmp_path, "baseline.yaml", BASELINE))


def test_a_missing_std_table_is_refused(tmp_path):
    empty = tmp_path / "empty.duckdb"
    with duckdb.connect(str(empty)) as con:
        con.execute("CREATE TABLE other AS SELECT 1 AS x")
    with pytest.raises(ValueError, match="std_customers"):
        blocking.run(empty, write_config(tmp_path, "blocking.yaml", BLOCKING))


# --- config validation --------------------------------------------------------


@pytest.mark.parametrize(
    "bad, message",
    [
        ({"rules": [{**SURNAME, "id": "Surname"}]}, "lowercase identifier"),
        ({"rules": [{**SURNAME, "id": "a; DROP TABLE x"}]}, "lowercase identifier"),
        ({"rules": [{**SURNAME, "id": "union"}]}, "reserved"),
        ({"rules": [SURNAME, SURNAME]}, "duplicate id"),
        ({"rules": [{"id": "x", "keys": ["surname_std"]}]}, "missing description"),
        ({"rules": [{"id": "x", "description": "d"}]}, "missing keys"),
        ({"rules": [{**SURNAME, "keys": []}]}, "non-empty list of keys"),
        ({"rules": [{**SURNAME, "keys": "surname_std"}]}, "non-empty list of keys"),
        ({"rules": [{**SURNAME, "keys": [{"field": "surname_std", "prefx": 1}]}]}, "'field'"),
        ({"rules": [{**SURNAME, "keys": [{"field": "surname_std", "prefix": 0}]}]}, "prefix"),
        ({"rules": [{**SURNAME, "keys": [{"field": "surname_std", "prefix": True}]}]}, "prefix"),
        ({"rules": [{**SURNAME, "keys": [{"field": "surname_std", "prefix": "1"}]}]}, "prefix"),
        ({"rules": [{**SURNAME, "keys": ["no_such_column"]}]}, "not a column"),
        ({"rules": [{**SURNAME, "keys": [7]}]}, "column name or a mapping"),
        ({"rules": "surname"}, "must be a list"),
        ({}, "missing 'rules'"),
    ],
)
def test_a_bad_blocking_config_is_refused(tmp_path, bad, message):
    columns = {"unique_id", "surname_std"}
    with pytest.raises(ValueError, match=message):
        blocking.load_rules(write_config(tmp_path, "bad.yaml", bad), columns)


@pytest.mark.parametrize(
    "bad, message",
    [
        ({"variants": [{"id": "x", "description": "d"}]}, "missing match_on"),
        ({"variants": [{"id": "x", "description": "d", "match_on": []}]}, "non-empty list of keys"),
        ({"variants": [{"id": "x", "description": "d", "match_on": [{"field": "surname_std", "prefix": 1}]}]}, "column names"),
        ({"variants": [{"id": "x", "description": "d", "match_on": ["no_such_column"]}]}, "not a column"),
        ({"variants": [{"id": "x", "description": "d", "match_on": ["surname_std"]}] * 2}, "duplicate id"),
        ({}, "missing 'variants'"),
    ],
)
def test_a_bad_baseline_config_is_refused(tmp_path, bad, message):
    with pytest.raises(ValueError, match=message):
        baseline.load_variants(write_config(tmp_path, "bad.yaml", bad), {"unique_id", "surname_std"})


def test_a_missing_rules_file_is_an_error_not_an_empty_rule_set(tmp_path):
    with pytest.raises(FileNotFoundError):
        baseline.load_variants(tmp_path / "absent.yaml")
    with pytest.raises(FileNotFoundError):
        blocking.load_rules(tmp_path / "absent.yaml")


def test_the_committed_configs_load_against_the_real_std_columns():
    """Every committed key must name a column the standardization step really writes."""
    config = dq_rules.load_config()
    columns = set(standardize.CARRIED_COLUMNS) | {
        f"{field}{standardize.STD_SUFFIX}" for field, _ in standardize.standardized_fields(config)
    }
    variants = baseline.load_variants(columns=columns)
    rules = blocking.load_rules(columns=columns)
    assert variants, "the committed baseline config holds no variants"
    assert rules, "the committed blocking config holds no rules"
    ids = [variant_id for variant_id, _ in variants] + [rule_id for rule_id, _ in rules]
    assert all(ids)
