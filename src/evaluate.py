"""Phase 3 evaluation against ground truth, authorized by the owner.

Inputs are canonical unordered pairs of opaque IDs, without labels. Evaluation
uses all raw customers as its reference population, including pairs absent from
blocking. Functions are read-only; the pipeline caller persists their results.
Undefined ratios return None (JSON null), never NaN or a misleading zero.
"""

from __future__ import annotations

from pathlib import Path
import re

import duckdb


def _counts(db_path: Path | str, pairs_table: str) -> tuple[int, int, int]:
    """Validate the pair contract and return TP, FP, FN over the full population."""
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", pairs_table):
        raise ValueError("pairs_table must be a simple SQL identifier")
    table = f'"{pairs_table}"'
    with duckdb.connect(str(db_path), read_only=True) as con:
        columns = [row[0] for row in con.execute(f"DESCRIBE {table}").fetchall()]
        if set(columns) != {"unique_id_l", "unique_id_r"} or len(columns) != 2:
            raise ValueError("pair tables must contain exactly unique_id_l and unique_id_r")
        invalid_truth = con.execute("""
            SELECT count(*) != count(DISTINCT unique_id)
                OR count(*) != count(true_cluster_id)
            FROM raw_customers
        """).fetchone()[0]
        if invalid_truth:
            raise ValueError("ground truth requires unique, non-null IDs and non-null labels")
        invalid_pairs = con.execute(f"""
            SELECT count(*) FROM {table} p
            LEFT JOIN raw_customers l ON p.unique_id_l = l.unique_id
            LEFT JOIN raw_customers r ON p.unique_id_r = r.unique_id
            WHERE p.unique_id_l IS NULL OR p.unique_id_r IS NULL
                OR p.unique_id_l >= p.unique_id_r
                OR l.unique_id IS NULL OR r.unique_id IS NULL
        """).fetchone()[0]
        duplicates = con.execute(f"""
            SELECT count(*) FROM (
                SELECT unique_id_l, unique_id_r FROM {table}
                GROUP BY unique_id_l, unique_id_r HAVING count(*) > 1
            )
        """).fetchone()[0]
        if invalid_pairs or duplicates:
            raise ValueError("pairs must be unique, ordered, non-self pairs of known non-null IDs")
        total_true = int(con.execute("""
            SELECT coalesce(sum(n * (n - 1) // 2), 0)
            FROM (SELECT count(*) AS n FROM raw_customers GROUP BY true_cluster_id)
        """).fetchone()[0])
        predicted, tp = con.execute(f"""
            SELECT count(*), count(*) FILTER (WHERE l.true_cluster_id = r.true_cluster_id)
            FROM {table} p
            JOIN raw_customers l ON p.unique_id_l = l.unique_id
            JOIN raw_customers r ON p.unique_id_r = r.unique_id
        """).fetchone()
    return tp, predicted - tp, total_true - tp


def _ratio(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def pairwise_metrics(db_path: Path | str, pairs_table: str) -> dict:
    """Score declared-match pairs against raw_customers joined on unique_id.

    Return true_positives, false_positives, false_negatives, precision, recall,
    and f1. All true pairs in the raw population form the recall denominator.
    Zero denominators return None. F1 uses 2TP/(2TP+FP+FN), so an empty
    prediction table has F1 zero if true pairs exist, otherwise None.
    Malformed pair tables or incomplete ground truth raise ValueError.
    """
    tp, fp, fn = _counts(db_path, pairs_table)
    return {
        "true_positives": tp,
        "false_positives": fp,
        "false_negatives": fn,
        "precision": _ratio(tp, tp + fp),
        "recall": _ratio(tp, tp + fn),
        "f1": _ratio(2 * tp, 2 * tp + fp + fn),
    }


def pair_completeness(db_path: Path | str, pairs_table: str) -> float | None:
    """Return surviving true pairs / all true pairs for a candidate pair table.

    Ground truth is joined on unique_id. Return None if no true pairs exist;
    otherwise return a number in [0, 1]. Validate the same contract as pairwise
    scoring. A union must already be deduplicated by the candidate generator.
    """
    tp, _, fn = _counts(db_path, pairs_table)
    return _ratio(tp, tp + fn)
