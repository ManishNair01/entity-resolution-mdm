"""Guard test: `raw_customers` must survive a pipeline run unchanged.

Every stage reads from DuckDB and writes a *new* table (AGENTS.md architecture
rule 1). This test fingerprints `raw_customers` after ingest, runs the whole
pipeline, and fails if the row count or the content hash moved. Because ingest is
itself part of the pipeline, it also proves the table is reproducible from a fixed
seed rather than accumulating changes run to run.
"""

import hashlib

import duckdb
import pytest

import run_pipeline
from src import ingest, profile


def fingerprint(db_path) -> tuple[int, str]:
    """Return (row count, content hash) for `raw_customers`, order-independent."""
    with duckdb.connect(str(db_path)) as con:
        frame = con.execute(
            f"SELECT * FROM {ingest.TABLE_NAME} ORDER BY ALL"
        ).fetch_df()
    payload = frame.to_csv(index=False).encode("utf-8")
    return len(frame), hashlib.sha256(payload).hexdigest()


@pytest.fixture(scope="module")
def ingested_db(tmp_path_factory, request):
    """Ingest into a throwaway DuckDB file, leaving the project's own outputs alone.

    Every output path any stage writes to is redirected here, including the
    profile report; otherwise running `pytest` would overwrite `reports/profile.md`.
    """
    tmp = tmp_path_factory.mktemp("mdm")
    monkeypatch = pytest.MonkeyPatch()
    request.addfinalizer(monkeypatch.undo)
    monkeypatch.setattr(ingest, "METRICS_PATH", tmp / "metrics.json")
    monkeypatch.setattr(ingest, "RAW_SNAPSHOT_PATH", tmp / "febrl3.csv")
    monkeypatch.setattr(profile, "REPORT_PATH", tmp / "profile.md")
    monkeypatch.setattr(profile, "PROBLEMS_PATH", tmp / "problems_observed.md")

    db_path = tmp / "mdm.duckdb"
    metrics = ingest.run(db_path)
    return db_path, metrics


def test_raw_customers_unchanged_by_pipeline(ingested_db):
    db_path, _ = ingested_db
    before = fingerprint(db_path)

    run_pipeline.run(db_path)

    after = fingerprint(db_path)
    assert after == before, (
        f"{ingest.TABLE_NAME} changed during the pipeline run: "
        f"{before} -> {after}"
    )


def test_ingest_is_reproducible(ingested_db, tmp_path):
    """Acceptance check: running ingest twice produces identical tables."""
    first_db, _ = ingested_db
    second_db = tmp_path / "again.duckdb"
    ingest.run(second_db)

    assert fingerprint(second_db) == fingerprint(first_db)


def test_ingest_does_not_depend_on_source_row_order(monkeypatch):
    """Row order from `recordlinkage` must not change the table.

    Every derived value is a hash of the record's own ID, so re-ordering the input
    must produce an identical frame. If this fails, the pipeline has picked up a
    dependency on the order the dataset package happens to return.
    """
    baseline = ingest.build_raw_customers()

    original_loader = ingest.load_source_frame
    monkeypatch.setattr(
        ingest,
        "load_source_frame",
        lambda: original_loader().sort_values("rec_id").reset_index(drop=True),
    )
    reordered = ingest.build_raw_customers()

    assert reordered.equals(baseline)


def test_true_entity_count_matches_originals(ingested_db):
    """Acceptance check: distinct entities == the number of `-org` records observed."""
    _, metrics = ingested_db
    assert metrics["ingest.true_entity_count"] == metrics["ingest.original_record_count"]
    assert (
        metrics["ingest.record_count"]
        == metrics["ingest.original_record_count"] + metrics["ingest.duplicate_record_count"]
    )


def test_pipeline_does_not_write_project_reports(ingested_db):
    """A test run must write its report to the temp directory, not `reports/`."""
    db_path, _ = ingested_db
    project_report = profile.PROJECT_ROOT / "reports" / "profile.md"
    before = project_report.stat().st_mtime_ns if project_report.exists() else None

    run_pipeline.run(db_path)

    after = project_report.stat().st_mtime_ns if project_report.exists() else None
    assert after == before, "pipeline run under test touched reports/profile.md"
    assert profile.REPORT_PATH.exists(), "report was not written to the temp directory"
