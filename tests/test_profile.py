"""Tests for the Phase 1 profiling stage.

Two things are worth guarding here. The pattern SQL is the one piece of real
logic in the stage, so it is tested against values chosen to break it (mixed
case, separators, blanks). The rest checks that the numbers in the report are the
numbers in the data, on a tiny fixture where every count can be verified by hand.
"""

import duckdb
import pytest

from src import ingest, profile


@pytest.fixture()
def memory_connection():
    with duckdb.connect() as con:
        yield con


def apply(con, expression_builder, values):
    """Run one of the profile SQL expressions over `values`, in order."""
    con.execute("CREATE OR REPLACE TABLE sample (v VARCHAR)")
    con.executemany("INSERT INTO sample VALUES (?)", [(value,) for value in values])
    sql = expression_builder("v")
    rows = con.execute(f"SELECT {sql} FROM sample").fetchall()
    return [row[0] for row in rows]


def test_pattern_masks_digits_and_letters_but_keeps_separators(memory_connection):
    values = ["19420804", "1942-08-04", "nsw", "NSW", "mary-jane", "unit 3a", None, ""]
    assert apply(memory_connection, profile.pattern_expression, values) == [
        "99999999",
        "9999-99-99",
        "AAA",
        "AAA",
        "AAAA-AAAA",
        "AAAA 9A",
        None,
        "",
    ]


def test_shape_collapses_runs_of_one_symbol(memory_connection):
    values = ["19420804", "1942-08-04", "mary-jane", "unit 3a", "a  b", None]
    assert apply(memory_connection, profile.shape_expression, values) == [
        "9",
        "9-9-9",
        "A-A",
        "A 9A",
        # A repeated separator is not collapsed: a double space is drift worth seeing.
        "A  A",
        None,
    ]


def test_populated_expression_treats_blank_as_missing(memory_connection):
    values = ["nsw", "", "   ", None, " vic "]
    assert apply(memory_connection, profile.populated_expression, values) == [
        "nsw",
        None,
        None,
        None,
        "vic",
    ]


# --- A tiny dataset where every count can be checked by hand -------------------

ROWS = [
    # given_name, surname, postcode, state, date_of_birth
    ("anna", "smith", "2000", "nsw", "19800101"),
    ("anna", "smith", "2000", "nsw", "1980-01-01"),
    ("anna", "jones", "2001", "vic", "19800101"),
    ("bob", "jones", "2001", "", "19800102"),
    ("bob", None, "2001", "   ", None),
]
# Entity sizes in the fixture: one entity of 3 records, one of 2.
CLUSTER_SIZES = [(2, 1, 2), (3, 1, 3)]


@pytest.fixture()
def tiny_db(tmp_path, monkeypatch):
    """Build a five-row `raw_customers` with the columns the profiler reads."""
    monkeypatch.setattr(profile, "PROFILED_COLUMNS", ["given_name", "surname", "postcode",
                                                      "state", "date_of_birth"])
    db_path = tmp_path / "tiny.duckdb"
    with duckdb.connect(str(db_path)) as con:
        con.execute(
            f"""
            CREATE TABLE {profile.SOURCE_TABLE} (
                unique_id BIGINT,
                given_name VARCHAR, surname VARCHAR, postcode VARCHAR,
                state VARCHAR, date_of_birth VARCHAR
            )
            """
        )
        con.executemany(
            f"INSERT INTO {profile.SOURCE_TABLE} VALUES (?, ?, ?, ?, ?, ?)",
            [(index, *row) for index, row in enumerate(ROWS)],
        )
        con.execute(
            f"CREATE TABLE {profile.CLUSTER_SIZE_TABLE} "
            "(cluster_size BIGINT, entity_count BIGINT, record_count BIGINT)"
        )
        con.executemany(
            f"INSERT INTO {profile.CLUSTER_SIZE_TABLE} VALUES (?, ?, ?)", CLUSTER_SIZES
        )
    return db_path


@pytest.fixture()
def tiny_profile(tiny_db, tmp_path, monkeypatch):
    """Profile the tiny database, keeping all output inside the temp directory."""
    monkeypatch.setattr(ingest, "METRICS_PATH", tmp_path / "metrics.json")
    report_path = tmp_path / "profile.md"
    metrics = profile.run(tiny_db, report_path=report_path)
    return metrics, report_path


def test_completeness_counts_blank_and_null_as_missing(tiny_profile):
    metrics, _ = tiny_profile
    # `state` holds one NULL-free empty string and one whitespace-only value.
    assert metrics["profile.columns.state.null_count"] == 0
    assert metrics["profile.columns.state.empty_count"] == 2
    assert metrics["profile.columns.state.populated_count"] == 3
    assert metrics["profile.columns.state.completeness_rate"] == 0.6
    # `surname` holds a real NULL.
    assert metrics["profile.columns.surname.null_count"] == 1
    assert metrics["profile.columns.surname.empty_count"] == 0
    assert metrics["profile.columns.surname.distinct_count"] == 2


def test_every_profiled_column_has_a_completeness_figure(tiny_profile):
    """Phase 1 acceptance check."""
    metrics, _ = tiny_profile
    for column in profile.PROFILED_COLUMNS:
        assert f"profile.columns.{column}.completeness_rate" in metrics


def test_pattern_counts_separate_format_drift(tiny_profile):
    metrics, _ = tiny_profile
    # `19800101` twice and `1980-01-01` once: two patterns, two shapes.
    assert metrics["profile.columns.date_of_birth.distinct_pattern_count"] == 2
    assert metrics["profile.columns.date_of_birth.distinct_shape_count"] == 2
    # Postcodes are all four digits, so one pattern that collapses to one shape.
    assert metrics["profile.columns.postcode.distinct_pattern_count"] == 1
    assert metrics["profile.columns.postcode.distinct_shape_count"] == 1


def test_ground_truth_duplication_comes_from_the_aggregate(tiny_profile):
    metrics, _ = tiny_profile
    assert metrics["profile.ground_truth.record_count"] == 5
    assert metrics["profile.ground_truth.entity_count"] == 2
    assert metrics["profile.ground_truth.records_per_entity"] == 2.5
    assert metrics["profile.ground_truth.redundant_record_count"] == 3
    assert metrics["profile.ground_truth.min_cluster_size"] == 2
    assert metrics["profile.ground_truth.max_cluster_size"] == 3
    assert metrics["profile.ground_truth.singleton_entity_count"] == 0


def test_top_values_are_ranked_and_tie_broken_by_value(tiny_db, tmp_path, monkeypatch):
    monkeypatch.setattr(ingest, "METRICS_PATH", tmp_path / "metrics.json")
    profile.run(tiny_db, report_path=tmp_path / "profile.md")
    with duckdb.connect(str(tiny_db)) as con:
        rows = con.execute(
            f"SELECT value, frequency FROM {profile.TOP_VALUE_TABLE} "
            "WHERE column_name = 'given_name' ORDER BY rank"
        ).fetchall()
    # anna (3) outranks bob (2); ties elsewhere fall back to the value itself.
    assert rows == [("anna", 3), ("bob", 2)]


def test_report_is_byte_identical_across_runs(tiny_db, tmp_path, monkeypatch):
    """Architecture rule 4: two runs must give identical output."""
    monkeypatch.setattr(ingest, "METRICS_PATH", tmp_path / "metrics.json")
    first = tmp_path / "first.md"
    second = tmp_path / "second.md"
    profile.run(tiny_db, report_path=first)
    profile.run(tiny_db, report_path=second)
    assert first.read_text(encoding="utf-8") == second.read_text(encoding="utf-8")


def test_placeholder_is_written_when_the_owner_has_not_filled_the_list_in(tiny_profile):
    _, report_path = tiny_profile
    text = report_path.read_text(encoding="utf-8")
    assert profile.PROBLEMS_START in text and profile.PROBLEMS_END in text
    assert "[TBD]" in text


def test_owner_problem_list_survives_regeneration(tiny_db, tmp_path, monkeypatch):
    """The one hand-written section must not be erased by the next pipeline run."""
    monkeypatch.setattr(ingest, "METRICS_PATH", tmp_path / "metrics.json")
    report_path = tmp_path / "profile.md"
    profile.run(tiny_db, report_path=report_path)

    owner_text = "1. `nws` is a misspelt `nsw` (13 rows)."
    text = report_path.read_text(encoding="utf-8")
    start = text.index(profile.PROBLEMS_START) + len(profile.PROBLEMS_START)
    end = text.index(profile.PROBLEMS_END)
    report_path.write_text(text[:start] + f"\n{owner_text}\n" + text[end:], encoding="utf-8")

    profile.run(tiny_db, report_path=report_path)
    regenerated = report_path.read_text(encoding="utf-8")
    assert owner_text in regenerated
    assert "[TBD]" not in regenerated


def test_profile_does_not_write_to_the_source_table(tiny_db, tmp_path, monkeypatch):
    """Architecture rule 1: the stage reads `raw_customers` and writes new tables."""
    monkeypatch.setattr(ingest, "METRICS_PATH", tmp_path / "metrics.json")
    with duckdb.connect(str(tiny_db)) as con:
        before = con.execute(f"SELECT * FROM {profile.SOURCE_TABLE} ORDER BY ALL").fetchall()

    profile.run(tiny_db, report_path=tmp_path / "profile.md")

    with duckdb.connect(str(tiny_db)) as con:
        after = con.execute(f"SELECT * FROM {profile.SOURCE_TABLE} ORDER BY ALL").fetchall()
        tables = {row[0] for row in con.execute("SHOW TABLES").fetchall()}
    assert after == before
    assert {
        profile.COLUMN_TABLE,
        profile.TOP_VALUE_TABLE,
        profile.PATTERN_TABLE,
        profile.CLUSTER_PROFILE_TABLE,
    } <= tables
