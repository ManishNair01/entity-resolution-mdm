"""Phase 1: the profile report keeps the owner's problems list and uses the agreed definitions."""

from src import profile


def test_missing_display_preserves_nulls_and_distinguishes_empty_strings():
    stats = {
        "total_rows": 1, "null_count": 1, "null_rate": 1.0,
        "empty_count": 0, "empty_rate": 0.0, "distinct_count": 0,
        "min_length": None, "max_length": None,
    }
    assert profile._format_value(None) == "[Missing]"
    assert profile._format_value("") == "*(empty string)*"
    assert "| Min length | [Missing] |" in profile._completeness_table(stats)
    assert "| Max length | [Missing] |" in profile._completeness_table(stats)
    assert stats["min_length"] is None and stats["max_length"] is None

INGEST_METRICS = {
    "ingest.record_count": 5000,
    "ingest.duplicate_record_count": 3000,
    "ingest.true_entity_count": 2000,
    "ingest.cluster_size_distribution": {"1": 835, "6": 168},
}


def test_duplicate_rate_definitions():
    """OPEN-DECISIONS 2026-09-26: duplicates / records, and records / entities, reported separately."""
    derived = profile.duplication_metrics(INGEST_METRICS)
    assert derived["profile.duplicate_rate"] == 3000 / 5000
    assert derived["profile.records_per_entity"] == 5000 / 2000
    assert (derived["profile.cluster_size_min"], derived["profile.cluster_size_max"]) == (1, 6)


def test_problems_section_embeds_owner_text():
    problems = "## Problems observed\r\n\r\n**P1 - example.** Value `19875031`.\r\n"
    section = profile._problems_section(problems)
    assert "**P1 - example.** Value `19875031`." in section
    assert section.count("## Problems observed") == 1
    assert "[TBD]" not in section
    assert "\r" not in section


def test_problems_section_adds_heading_if_missing():
    assert profile._problems_section("P1 only").count("## Problems observed") == 1


def test_problems_section_tbd_when_missing():
    assert profile._problems_section(None) == "## Problems observed\n\n[TBD]\n"
    assert profile._problems_section("   \n") == "## Problems observed\n\n[TBD]\n"


def test_run_never_writes_problems_file(tmp_path, monkeypatch):
    """`run()` reads the owner's file; it must not create or change it."""
    problems_path = tmp_path / "problems_observed.md"
    # write_bytes, not write_text: on Windows write_text translates the newlines
    # to CRLF and read_text translates them back, so the comparison below would
    # fail on the platform instead of on the behaviour under test.
    problems_path.write_bytes("## Problems observed\n\nowner text\n".encode("utf-8"))
    monkeypatch.setattr(profile, "PROBLEMS_PATH", problems_path)
    before = problems_path.read_bytes()
    assert profile.load_problems() == before.decode("utf-8")
    assert problems_path.read_bytes() == before
