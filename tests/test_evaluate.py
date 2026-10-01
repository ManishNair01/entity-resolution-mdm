"""Independent hand-calculated examples for Phase 3 evaluation."""
import duckdb
import pytest

from src.evaluate import pair_completeness, pairwise_metrics


def make_db(tmp_path, labels=("a", "a", "a", "b", "b", "c"), pairs=()):
    path = tmp_path / "evaluation.duckdb"
    with duckdb.connect(str(path)) as con:
        con.execute("CREATE TABLE raw_customers (unique_id INTEGER, true_cluster_id VARCHAR)")
        if labels:
            con.executemany("INSERT INTO raw_customers VALUES (?, ?)", list(enumerate(labels, 1)))
        con.execute("CREATE TABLE predictions (unique_id_l INTEGER, unique_id_r INTEGER)")
        if pairs:
            con.executemany("INSERT INTO predictions VALUES (?, ?)", pairs)
    return path


def test_mixed_predictions(tmp_path):
    # True pairs: 1-2, 1-3, 2-3, 4-5. Predictions recover two and invent one.
    db = make_db(tmp_path, pairs=[(1, 2), (4, 5), (3, 6)])
    assert pairwise_metrics(db, "predictions") == {
        "true_positives": 2, "false_positives": 1, "false_negatives": 2,
        "precision": 2 / 3, "recall": 1 / 2, "f1": 4 / 7,
    }
    assert pair_completeness(db, "predictions") == 1 / 2


def test_empty_predictions(tmp_path):
    db = make_db(tmp_path)
    assert pairwise_metrics(db, "predictions") == {
        "true_positives": 0, "false_positives": 0, "false_negatives": 4,
        "precision": None, "recall": 0.0, "f1": 0.0,
    }
    assert pair_completeness(db, "predictions") == 0.0


@pytest.mark.parametrize("labels", [(), ("a",), ("a", "b")])
def test_no_true_pairs_or_predictions(tmp_path, labels):
    db = make_db(tmp_path, labels=labels)
    result = pairwise_metrics(db, "predictions")
    assert result["precision"] is result["recall"] is result["f1"] is None
    assert pair_completeness(db, "predictions") is None


def test_only_false_predictions(tmp_path):
    db = make_db(tmp_path, labels=("a", "b"), pairs=[(1, 2)])
    result = pairwise_metrics(db, "predictions")
    assert result["precision"] == result["f1"] == 0.0
    assert result["recall"] is None


def test_overlapping_union(tmp_path):
    db = make_db(tmp_path, pairs=[(1, 2), (1, 3), (1, 6)])
    with duckdb.connect(str(db)) as con:
        con.execute("CREATE TABLE second AS SELECT * FROM (VALUES (1, 2), (2, 3), (4, 5)) t(unique_id_l, unique_id_r)")
        con.execute("CREATE TABLE combined AS SELECT * FROM predictions UNION SELECT * FROM second")
    assert pair_completeness(db, "predictions") == 1 / 2
    assert pair_completeness(db, "second") == 3 / 4
    assert pair_completeness(db, "combined") == 1.0
    result = pairwise_metrics(db, "combined")
    assert result["true_positives"] == 4
    assert result["false_positives"] == 1
    assert result["false_negatives"] == 0
    assert result["precision"] == 4 / 5
    assert result["f1"] == 8 / 9


@pytest.mark.parametrize("pairs", [[(1, 1)], [(2, 1)], [(1, 99)], [(None, 2)], [(1, 2), (1, 2)]])
def test_invalid_pairs_rejected(tmp_path, pairs):
    db = make_db(tmp_path, pairs=pairs)
    with pytest.raises(ValueError):
        pairwise_metrics(db, "predictions")


def test_invalid_truth_rejected(tmp_path):
    db = make_db(tmp_path, labels=(None, "a"))
    with pytest.raises(ValueError, match="ground truth"):
        pair_completeness(db, "predictions")


def test_table_name_not_sql(tmp_path):
    db = make_db(tmp_path)
    with pytest.raises(ValueError, match="identifier"):
        pairwise_metrics(db, "predictions; DROP TABLE raw_customers")
