"""Phase 1 — profile `raw_customers`: completeness, distinct counts, top
values, length bounds, and format patterns per column, written to
`reports/profile.md`.

The ground-truth duplicate rate and cluster-size distribution shown in the
report are *read back* from `reports/metrics.json` rather than computed here:
AGENTS.md hard rule 1 only lets `ingest.py` (and `evaluate.py`) touch the
ground-truth columns, and `ingest.py` already writes the cluster-size
distribution for this module to read.

The "problems observed" list is the owner's to write (roadmap Phase 1,
Section 10.1). It lives in `reports/problems_observed.md`, which this module
only ever *reads* and embeds at the end of the report, so regenerating
`profile.md` can never erase it. If that file is missing, the section is `[TBD]`.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import duckdb

from src import ingest
from src.ingest import DEFAULT_DB_PATH, FEBRL_COLUMNS, TABLE_NAME, write_metrics

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = PROJECT_ROOT / "reports" / "profile.md"
# Owner-written, never written by this module.
PROBLEMS_PATH = PROJECT_ROOT / "reports" / "problems_observed.md"

# The two synthetic metadata columns (roadmap Section 2) are worth profiling
# alongside the Febrl fields. `unique_id` (a hash-ordered surrogate key) and the
# guarded ground-truth column are deliberately excluded: the former has no
# data-quality story, the latter may not be referenced outside `ingest.py`.
SYNTHETIC_COLUMNS = ["source_system", "last_updated"]
PROFILE_COLUMNS = [*FEBRL_COLUMNS, *SYNTHETIC_COLUMNS]

TOP_N_VALUES = 10
TOP_N_PATTERNS = 10


def pattern_expr(column: str) -> str:
    """DuckDB SQL expression mapping `column` to a format pattern.

    Every digit becomes `9` and every ASCII letter becomes `A`; everything
    else (spaces, punctuation) is left alone, so e.g. `"2/48"` -> `"9/99"` and
    `"O'Brien"` -> `"A'AAAAA"`. This exposes format drift within a column
    (mixed lengths, stray punctuation, digits where letters are expected)
    without looking at the values themselves.
    """
    text = f"CAST({column} AS VARCHAR)"
    digits_folded = f"regexp_replace({text}, '[0-9]', '9', 'g')"
    return f"regexp_replace({digits_folded}, '[A-Za-z]', 'A', 'g')"


def profile_column(con: duckdb.DuckDBPyConnection, column: str) -> dict[str, Any]:
    """Run the completeness / distinct / length / top-value / pattern queries for one column."""
    total_rows, null_count, empty_count, distinct_count, min_length, max_length = con.execute(
        f"""
        SELECT
            COUNT(*) AS total_rows,
            COUNT(*) FILTER (WHERE {column} IS NULL) AS null_count,
            COUNT(*) FILTER (
                WHERE {column} IS NOT NULL AND TRIM(CAST({column} AS VARCHAR)) = ''
            ) AS empty_count,
            COUNT(DISTINCT {column}) AS distinct_count,
            MIN(LENGTH(CAST({column} AS VARCHAR))) FILTER (WHERE {column} IS NOT NULL) AS min_length,
            MAX(LENGTH(CAST({column} AS VARCHAR))) FILTER (WHERE {column} IS NOT NULL) AS max_length
        FROM {TABLE_NAME}
        """
    ).fetchone()

    top_values = con.execute(
        f"""
        SELECT CAST({column} AS VARCHAR) AS value, COUNT(*) AS n
        FROM {TABLE_NAME}
        WHERE {column} IS NOT NULL
        GROUP BY value
        ORDER BY n DESC, value
        LIMIT {TOP_N_VALUES}
        """
    ).fetchall()

    pattern_sql = pattern_expr(column)
    distinct_pattern_count = con.execute(
        f"SELECT COUNT(DISTINCT {pattern_sql}) FROM {TABLE_NAME} WHERE {column} IS NOT NULL"
    ).fetchone()[0]

    top_patterns = con.execute(
        f"""
        SELECT {pattern_sql} AS pattern, COUNT(*) AS n
        FROM {TABLE_NAME}
        WHERE {column} IS NOT NULL
        GROUP BY pattern
        ORDER BY n DESC, pattern
        LIMIT {TOP_N_PATTERNS}
        """
    ).fetchall()

    return {
        "total_rows": int(total_rows),
        "null_count": int(null_count),
        "null_rate": (null_count / total_rows) if total_rows else 0.0,
        "empty_count": int(empty_count),
        "empty_rate": (empty_count / total_rows) if total_rows else 0.0,
        "distinct_count": int(distinct_count),
        "min_length": None if min_length is None else int(min_length),
        "max_length": None if max_length is None else int(max_length),
        "top_values": [{"value": value, "count": int(n)} for value, n in top_values],
        "distinct_pattern_count": int(distinct_pattern_count),
        "top_patterns": [{"pattern": pattern, "count": int(n)} for pattern, n in top_patterns],
    }


def profile_table(db_path: Path | str = DEFAULT_DB_PATH) -> dict[str, dict[str, Any]]:
    """Profile every column in `PROFILE_COLUMNS`, read-only."""
    with duckdb.connect(str(db_path), read_only=True) as con:
        return {column: profile_column(con, column) for column in PROFILE_COLUMNS}


def flatten_metrics(profile: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Namespace each column's stats as `profile.<column>.<key>` for metrics.json."""
    metrics: dict[str, Any] = {}
    for column, stats in profile.items():
        for key, value in stats.items():
            metrics[f"profile.{column}.{key}"] = value
    return metrics


def unflatten_profile(metrics: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Inverse of `flatten_metrics`: rebuild per-column stats from `profile.<column>.<key>` entries."""
    profile: dict[str, dict[str, Any]] = {}
    for column in PROFILE_COLUMNS:
        prefix = f"profile.{column}."
        profile[column] = {
            key[len(prefix):]: value for key, value in metrics.items() if key.startswith(prefix)
        }
    return profile


def load_existing_metrics(path: Path | str | None = None) -> dict[str, Any]:
    """Read `reports/metrics.json`.

    The default path is looked up on `ingest` at call time, not bound at import,
    so it always matches the file `write_metrics` just wrote to (and a test that
    redirects `ingest.METRICS_PATH` redirects this read too).
    """
    path = Path(path) if path is not None else ingest.METRICS_PATH
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def duplication_metrics(existing_metrics: dict[str, Any]) -> dict[str, Any]:
    """Derive duplicate rate, records per entity and cluster-size bounds from `ingest.py`'s metrics.

    Definitions (OPEN-DECISIONS.md, 2026-09-26):
    - duplicate rate = duplicate records / total records
    - records per entity = total records / true entities

    Reads only already-published numbers out of `reports/metrics.json`; never
    touches the ground-truth columns themselves (AGENTS.md hard rule 1).
    """
    record_count = existing_metrics.get("ingest.record_count")
    duplicate_record_count = existing_metrics.get("ingest.duplicate_record_count")
    true_entity_count = existing_metrics.get("ingest.true_entity_count")
    distribution = existing_metrics.get("ingest.cluster_size_distribution")

    metrics: dict[str, Any] = {}
    if duplicate_record_count is not None and record_count:
        metrics["profile.duplicate_rate"] = duplicate_record_count / record_count
    if record_count is not None and true_entity_count:
        metrics["profile.records_per_entity"] = record_count / true_entity_count
    if distribution:
        sizes = [int(size) for size in distribution]
        metrics["profile.cluster_size_min"] = min(sizes)
        metrics["profile.cluster_size_max"] = max(sizes)
    return metrics


def _format_value(value: Any) -> str:
    if value == "":
        return "*(empty string)*"
    return str(value).replace("|", "\\|")


def _completeness_table(stats: dict[str, Any]) -> str:
    lines = [
        "| Metric | Value |",
        "|---|---|",
        f"| Rows | {stats['total_rows']} |",
        f"| Null count | {stats['null_count']} |",
        f"| Null rate | {stats['null_rate']:.2%} |",
        f"| Empty-string count | {stats['empty_count']} |",
        f"| Empty-string rate | {stats['empty_rate']:.2%} |",
        f"| Distinct count | {stats['distinct_count']} |",
        f"| Min length | {stats['min_length']} |",
        f"| Max length | {stats['max_length']} |",
    ]
    return "\n".join(lines)


def _top_values_table(stats: dict[str, Any]) -> str:
    if not stats["top_values"]:
        return "*(no non-null values)*"
    lines = ["| Value | Count |", "|---|---|"]
    lines += [f"| {_format_value(row['value'])} | {row['count']} |" for row in stats["top_values"]]
    return "\n".join(lines)


def _pattern_table(stats: dict[str, Any]) -> str:
    header = f"{stats['distinct_pattern_count']} distinct pattern(s). Top {TOP_N_PATTERNS} by count:"
    if not stats["top_patterns"]:
        return f"{header}\n\n*(no non-null values)*"
    lines = [header, "", "| Pattern | Count |", "|---|---|"]
    lines += [f"| {_format_value(row['pattern'])} | {row['count']} |" for row in stats["top_patterns"]]
    return "\n".join(lines)


def _duplication_section(metrics: dict[str, Any]) -> str:
    record_count = metrics.get("ingest.record_count")
    duplicate_record_count = metrics.get("ingest.duplicate_record_count")
    true_entity_count = metrics.get("ingest.true_entity_count")
    distribution = metrics.get("ingest.cluster_size_distribution")
    derived_keys = [
        "profile.duplicate_rate",
        "profile.records_per_entity",
        "profile.cluster_size_min",
        "profile.cluster_size_max",
    ]

    if (
        record_count is None
        or duplicate_record_count is None
        or true_entity_count is None
        or not distribution
        or any(key not in metrics for key in derived_keys)
    ):
        return (
            "[TBD] — run `src/ingest.py` first; this section reads "
            "`ingest.record_count`, `ingest.duplicate_record_count`, "
            "`ingest.true_entity_count` and "
            "`ingest.cluster_size_distribution` from `reports/metrics.json`."
        )

    lines = [
        "| Metric | Value |",
        "|---|---|",
        f"| Records | {record_count} |",
        f"| True entities | {true_entity_count} |",
        f"| Duplicate records | {duplicate_record_count} |",
        f"| Duplicate rate (duplicate records / records) | {metrics['profile.duplicate_rate']:.2%} |",
        f"| Records per entity (records / entities) | {metrics['profile.records_per_entity']:.3f} |",
        f"| Cluster size, min | {metrics['profile.cluster_size_min']} |",
        f"| Cluster size, max | {metrics['profile.cluster_size_max']} |",
        "",
        "**Cluster-size distribution**",
        "",
        "| Cluster size | Number of clusters |",
        "|---|---|",
    ]
    for size in sorted(distribution, key=int):
        lines.append(f"| {size} | {distribution[size]} |")
    return "\n".join(lines)


def _problems_section(problems_text: str | None) -> str:
    """Owner's problems list, embedded verbatim; `[TBD]` if it hasn't been written."""
    if problems_text is None or not problems_text.strip():
        return "## Problems observed\n\n[TBD]\n"
    text = problems_text.replace("\r\n", "\n").strip()
    if not text.startswith("## "):
        text = "## Problems observed\n\n" + text
    note = (
        "<!-- Embedded from reports/problems_observed.md (owner-written). "
        "Edit that file, not this section: profile.md is regenerated on every run. -->"
    )
    return f"{note}\n\n{text}\n"


def load_problems(path: Path | str | None = None) -> str | None:
    """Read the owner's problems list, or return None if it doesn't exist yet."""
    path = Path(path) if path is not None else PROBLEMS_PATH
    return path.read_text(encoding="utf-8") if path.exists() else None


def format_report(metrics: dict[str, Any], problems_text: str | None = None) -> str:
    """Render `reports/profile.md` from `reports/metrics.json` plus the owner's problems list.

    Every number comes from `metrics`; the problems section is the owner's
    text, copied in unchanged.
    """
    profile = unflatten_profile(metrics)
    parts = [
        "# Data Profile — raw_customers",
        "",
        "All numbers below come from `reports/metrics.json`, written by "
        "`src/ingest.py` and `src/profile.py` (AGENTS.md architecture rule 3).",
        "",
        "## Duplicate rate and cluster sizes",
        "",
        _duplication_section(metrics),
        "",
        "## Column profiles",
        "",
    ]
    for column in PROFILE_COLUMNS:
        stats = profile[column]
        parts += [
            f"### `{column}`",
            "",
            "**Completeness**",
            "",
            _completeness_table(stats),
            "",
            f"**Top {TOP_N_VALUES} values**",
            "",
            _top_values_table(stats),
            "",
            "**Format patterns** (digits -> `9`, letters -> `A`)",
            "",
            _pattern_table(stats),
            "",
        ]
    parts.append(_problems_section(problems_text))
    return "\n".join(parts)


def run(db_path: Path | str = DEFAULT_DB_PATH) -> dict[str, Any]:
    """Profile `raw_customers`, write `reports/profile.md`, and return this stage's metrics."""
    profile = profile_table(db_path)
    metrics = flatten_metrics(profile)

    existing_metrics = load_existing_metrics()
    dup_metrics = duplication_metrics(existing_metrics)
    metrics.update(dup_metrics)

    write_metrics(metrics)

    # Render from the file just written, not the in-memory values, so every
    # number in the report is one that metrics.json actually holds.
    report = format_report(load_existing_metrics(), load_problems())
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(report, encoding="utf-8")

    return metrics


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default=str(DEFAULT_DB_PATH), help="path to the DuckDB file")
    args = parser.parse_args()

    run(args.db)
    print(f"wrote {REPORT_PATH}")


if __name__ == "__main__":
    main()
