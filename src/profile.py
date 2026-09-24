"""Phase 1 — profile `raw_customers` and write `reports/profile.md`.

The stage answers one question in numbers: how bad is this data before anything
touches it? Per column it measures completeness, cardinality, value lengths, the
ten most frequent values, and the format patterns behind them. It also reports
how duplicated the dataset is against ground truth.

Reading the rules that shape this module:

* **Hard rule 1 (no label leakage).** This module never sees the record
  identifier or the ground-truth label. The duplication figures come from
  `ground_truth_cluster_sizes`, an aggregate table that `ingest.py` writes and
  that carries counts per cluster size only -- no row is traceable to an entity
  from it. So the profile can report the duplicate rate without any code here
  being able to learn which records match.
* **Architecture rule 1 (new table per stage).** Everything here is read-only
  against `raw_customers`; the outputs are four new `profile_*` tables.
* **Architecture rule 4 (determinism).** Every ordering is fully specified
  (counts descending, then the value itself), and the report carries no
  timestamp, so two runs produce byte-identical output.
* **Rule 5 (owner-owned tasks).** The "problems observed" list is the owner's
  (roadmap section 10.1). The generator emits a `[TBD]` placeholder for it and,
  once the owner has written the list, preserves it verbatim across re-runs.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import duckdb

from src import ingest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB_PATH = ingest.DEFAULT_DB_PATH
REPORT_PATH = PROJECT_ROOT / "reports" / "profile.md"

SOURCE_TABLE = ingest.TABLE_NAME
CLUSTER_SIZE_TABLE = ingest.GROUND_TRUTH_TABLE

COLUMN_TABLE = "profile_columns"
TOP_VALUE_TABLE = "profile_top_values"
PATTERN_TABLE = "profile_patterns"
CLUSTER_PROFILE_TABLE = "profile_cluster_sizes"

# The columns worth profiling: the ten Febrl fields plus the two synthetic
# metadata columns. Deliberately excluded are the surrogate key, the source
# record identifier and the ground-truth label -- the first is generated here and
# has nothing to say about data quality, and the other two are ground truth that
# this module is not allowed to look at.
PROFILED_COLUMNS = [*ingest.FEBRL_COLUMNS, "source_system", "last_updated"]

TOP_N_VALUES = 10
TOP_N_PATTERNS = 10

PROBLEMS_START = "<!-- problems-observed:start -->"
PROBLEMS_END = "<!-- problems-observed:end -->"
PROBLEMS_PLACEHOLDER = (
    "[TBD] — owner-written (roadmap section 10.1). List at least five concrete\n"
    "problems seen in the tables above, each with a real example value, e.g. a\n"
    "misspelt state code or a name that appears in the wrong column. These become\n"
    "the candidate rules in Phase 2, so write them from what the profile actually\n"
    "shows rather than from what the dataset is supposed to contain.\n\n"
    "Anything written between the two `problems-observed` comment markers is kept\n"
    "when this report is regenerated; everything else in the file is overwritten."
)


def _columns(columns: list[str] | None) -> list[str]:
    """Resolve the column list, defaulting to `PROFILED_COLUMNS` at call time.

    Read at call time rather than bound as a default argument so that a caller --
    or a test -- can narrow the list without the module having to be reimported.
    """
    return list(PROFILED_COLUMNS) if columns is None else list(columns)


def value_expression(column: str) -> str:
    """Return the SQL that reads `column` as text.

    Profiling is about how values are *written*, so every column is compared as a
    string. Only `last_updated` is not already text; casting it keeps one code
    path for all columns instead of a typed special case.
    """
    return f'CAST("{column}" AS VARCHAR)'


def populated_expression(column: str) -> str:
    """Return the SQL for `column`'s value, or NULL when it is blank.

    A field holding an empty string or only spaces is missing data wearing a
    value's clothes, so completeness counts it as absent. The raw value is still
    profiled for length and pattern, which is where the whitespace shows up.
    """
    return f"NULLIF(TRIM({value_expression(column)}), '')"


def pattern_expression(column: str) -> str:
    """Return the SQL that maps a value to its format pattern.

    Every digit becomes `9` and every letter becomes `A`; anything else -- spaces,
    hyphens, slashes -- is left alone, because those separators are exactly where
    format drift shows (`19420804` against `1942-08-04`). Case is not
    distinguished: the roadmap specifies letters map to `A`, so `nsw` and `NSW`
    share a pattern. Case drift is therefore invisible here and is left to the
    Phase 2 standardization rules; see OPEN-DECISIONS.md.
    """
    digits_masked = f"regexp_replace({value_expression(column)}, '[0-9]', '9', 'g')"
    return f"regexp_replace({digits_masked}, '[A-Za-z]', 'A', 'g')"


def shape_expression(column: str) -> str:
    """Return the SQL for the pattern with runs of one symbol collapsed.

    `19420804` becomes `9` and `1942-08-04` becomes `9-9-9`; `mary-jane` becomes
    `A-A`. The plain pattern encodes length, so its top ten for a name column is
    ten different lengths and the handful of values carrying a hyphen, a space or
    a digit never surface. Collapsing runs throws length away and keeps the
    separators, which is where format drift lives. The two views answer different
    questions, so the report shows both. Runs of a separator are *not* collapsed,
    so a double space stays visible as one.
    """
    pattern = pattern_expression(column)
    return f"regexp_replace(regexp_replace({pattern}, '9+', '9', 'g'), 'A+', 'A', 'g')"


def column_stats_sql(columns: list[str] | None = None) -> str:
    """Build the per-column summary query: one row per profiled column.

    Written as a UNION ALL of one aggregate per column rather than an UNPIVOT so
    that each column's expressions stay readable and typed independently.
    """
    columns = _columns(columns)
    blocks = []
    for column in columns:
        raw = value_expression(column)
        populated = populated_expression(column)
        pattern = pattern_expression(column)
        shape = shape_expression(column)
        blocks.append(
            f"""
            SELECT
                '{column}' AS column_name,
                COUNT(*) AS row_count,
                COUNT({populated}) AS populated_count,
                COUNT(*) - COUNT({raw}) AS null_count,
                COUNT({raw}) - COUNT({populated}) AS empty_count,
                COUNT(*) - COUNT({populated}) AS missing_count,
                COUNT(DISTINCT {populated}) AS distinct_count,
                -- COALESCE so that a column with nothing in it reports 0 rather
                -- than NULL, which would break the metrics write.
                COALESCE(MIN(LENGTH({raw})) FILTER (WHERE {populated} IS NOT NULL), 0)
                    AS min_length,
                COALESCE(MAX(LENGTH({raw})) FILTER (WHERE {populated} IS NOT NULL), 0)
                    AS max_length,
                COUNT(DISTINCT {pattern}) FILTER (WHERE {populated} IS NOT NULL)
                    AS distinct_pattern_count,
                COUNT(DISTINCT {shape}) FILTER (WHERE {populated} IS NOT NULL)
                    AS distinct_shape_count
            FROM {SOURCE_TABLE}
            """
        )
    union = "\n            UNION ALL\n".join(block.strip() for block in blocks)
    # The ordinal keeps the report's column order equal to PROFILED_COLUMNS
    # instead of alphabetical, which would split the address fields apart.
    ordering = " ".join(f"WHEN '{c}' THEN {i}" for i, c in enumerate(columns))
    return f"""
        SELECT
            *,
            populated_count::DOUBLE / NULLIF(row_count, 0) AS completeness_rate
        FROM (
            {union}
        )
        ORDER BY CASE column_name {ordering} END
    """


def _ranked_frequency_sql(
    columns: list[str], expression, limit: int, label: str, kind: str | None = None
) -> str:
    """Build a top-N-per-column frequency query.

    `expression` turns a column name into the SQL being counted, so one query
    form serves both the top-values and the top-patterns tables. NULLs are left
    out: a missing value has no format, and its count is already in the
    per-column summary. Ties break on the value itself so that two runs rank
    equally frequent values identically (architecture rule 4).
    """
    kind_column = f"'{kind}' AS kind," if kind else ""
    # The literal columns come first, so the grouped value sits at position 2 or 3.
    group_by = "1, 2, 3" if kind else "1, 2"
    blocks = []
    for column in columns:
        target = expression(column)
        blocks.append(
            f"""
            SELECT
                '{column}' AS column_name,
                {kind_column}
                {target} AS {label},
                COUNT(*) AS frequency,
                ROW_NUMBER() OVER (
                    ORDER BY COUNT(*) DESC, {target} ASC
                ) AS rank
            FROM {SOURCE_TABLE}
            WHERE {populated_expression(column)} IS NOT NULL
            GROUP BY {group_by}
            QUALIFY rank <= {limit}
            """
        )
    union = "\n            UNION ALL\n".join(block.strip() for block in blocks)
    ordering = " ".join(f"WHEN '{c}' THEN {i}" for i, c in enumerate(columns))
    return f"""
        SELECT *
        FROM (
            {union}
        )
        ORDER BY CASE column_name {ordering} END, rank
    """


def top_values_sql(columns: list[str] | None = None, limit: int = TOP_N_VALUES) -> str:
    """Build the top-`limit`-values-per-column query."""
    return _ranked_frequency_sql(_columns(columns), value_expression, limit, "value")


def top_patterns_sql(columns: list[str] | None = None, limit: int = TOP_N_PATTERNS) -> str:
    """Build the top-`limit`-patterns-per-column query, in both views.

    One table holds both: `kind = 'pattern'` for the literal mapping and
    `kind = 'shape'` for the same pattern with runs collapsed.
    """
    columns = _columns(columns)
    patterns = _ranked_frequency_sql(columns, pattern_expression, limit, "pattern", "pattern")
    shapes = _ranked_frequency_sql(columns, shape_expression, limit, "pattern", "shape")
    return f"""
        SELECT * FROM ({patterns})
        UNION ALL
        SELECT * FROM ({shapes})
    """


def cluster_size_sql() -> str:
    """Build the cluster-size distribution query.

    Reads the aggregate `ground_truth_cluster_sizes` table, which holds one row
    per cluster size (how many entities have that many records). Shares are added
    here so the report never divides numbers itself.
    """
    return f"""
        SELECT
            cluster_size,
            entity_count,
            record_count,
            entity_count::DOUBLE / SUM(entity_count) OVER () AS entity_share,
            record_count::DOUBLE / SUM(record_count) OVER () AS record_share
        FROM {CLUSTER_SIZE_TABLE}
        ORDER BY cluster_size
    """


# --- Metrics ------------------------------------------------------------------


def sort_by_column_order(frame, *extra_keys: str):
    """Sort a profile frame into `PROFILED_COLUMNS` order, then by `extra_keys`.

    A `CREATE TABLE AS ... ORDER BY` does not promise an order when the table is
    read back, and alphabetical order would split `address_1` from `suburb`.
    Sorting here keeps the report's section order fixed run to run
    (architecture rule 4).
    """
    order = {column: index for index, column in enumerate(PROFILED_COLUMNS)}
    out = frame.copy()
    out["_column_order"] = out["column_name"].map(order)
    out = out.sort_values(["_column_order", *extra_keys], kind="stable")
    return out.drop(columns="_column_order").reset_index(drop=True)


def build_metrics(columns_frame, clusters_frame) -> dict:
    """Turn the two summary frames into the flat `reports/metrics.json` entries.

    Keys are namespaced by stage, matching `ingest.*`. Everything the report
    states as a headline number is here; the per-value detail in the top-values
    and pattern tables stays in DuckDB, since those are thousands of rows rather
    than metrics (see OPEN-DECISIONS.md).
    """
    row_count = int(columns_frame["row_count"].iloc[0]) if len(columns_frame) else 0
    metrics: dict = {
        "profile.row_count": row_count,
        "profile.profiled_column_count": int(len(columns_frame)),
    }

    for row in columns_frame.itertuples(index=False):
        prefix = f"profile.columns.{row.column_name}"
        metrics[f"{prefix}.populated_count"] = int(row.populated_count)
        metrics[f"{prefix}.null_count"] = int(row.null_count)
        metrics[f"{prefix}.empty_count"] = int(row.empty_count)
        metrics[f"{prefix}.missing_count"] = int(row.missing_count)
        metrics[f"{prefix}.completeness_rate"] = round(float(row.completeness_rate), 6)
        metrics[f"{prefix}.distinct_count"] = int(row.distinct_count)
        metrics[f"{prefix}.min_length"] = int(row.min_length)
        metrics[f"{prefix}.max_length"] = int(row.max_length)
        metrics[f"{prefix}.distinct_pattern_count"] = int(row.distinct_pattern_count)
        metrics[f"{prefix}.distinct_shape_count"] = int(row.distinct_shape_count)

    entity_count = int(clusters_frame["entity_count"].sum())
    duplicated_record_count = int(clusters_frame["record_count"].sum())
    metrics.update(
        {
            "profile.ground_truth.entity_count": entity_count,
            "profile.ground_truth.record_count": duplicated_record_count,
            # The duplicate rate the roadmap asks for: records divided by true
            # entities. 1.0 would mean no duplication at all.
            "profile.ground_truth.records_per_entity": round(
                duplicated_record_count / entity_count, 6
            )
            if entity_count
            else 0.0,
            "profile.ground_truth.redundant_record_count": duplicated_record_count - entity_count,
            "profile.ground_truth.min_cluster_size": int(clusters_frame["cluster_size"].min()),
            "profile.ground_truth.max_cluster_size": int(clusters_frame["cluster_size"].max()),
            "profile.ground_truth.singleton_entity_count": int(
                clusters_frame.loc[clusters_frame["cluster_size"] == 1, "entity_count"].sum()
            ),
        }
    )
    return metrics


# --- Report -------------------------------------------------------------------


def _cell(value) -> str:
    """Render one table cell, keeping the value readable and the table intact."""
    text = "" if value is None else str(value)
    return text.replace("|", "\\|")


def _code_cell(value) -> str:
    """Render a data value in backticks, so leading or trailing spaces show up."""
    return f"`{_cell(value)}`"


def _md_table(headers: list[str], rows: list[list[str]]) -> str:
    """Render a GitHub-flavoured Markdown table."""
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    lines.extend("| " + " | ".join(row) + " |" for row in rows)
    return "\n".join(lines)


def _count(value) -> str:
    return f"{int(value):,}"


def _percent(value) -> str:
    return f"{float(value) * 100:.2f}%"


def existing_problems_section(path: Path) -> str | None:
    """Return the owner's "problems observed" prose from an earlier report, if any.

    The report is regenerated on every pipeline run, which would otherwise erase
    the one section a human writes by hand. Anything between the two markers is
    carried over; the placeholder itself is not, so an untouched report keeps
    showing `[TBD]` (hard rule 2: no invented numbers, leave the gap visible).
    """
    if not path.exists():
        return None
    text = path.read_text(encoding="utf-8")
    start = text.find(PROBLEMS_START)
    end = text.find(PROBLEMS_END)
    if start == -1 or end == -1 or end < start:
        return None
    body = text[start + len(PROBLEMS_START) : end].strip()
    if not body or body == PROBLEMS_PLACEHOLDER.strip():
        return None
    return body


def render_report(metrics: dict, columns_frame, top_values_frame, patterns_frame,
                  clusters_frame, problems: str | None = None) -> str:
    """Render `reports/profile.md` from this run's tables and metrics.

    No timestamp and no "generated on" line: the report is committed, and a clock
    reading would make two identical runs produce different files (architecture
    rule 4).
    """
    row_count = metrics["profile.row_count"]
    parts: list[str] = [
        "# Data profile — `raw_customers`",
        "",
        "Phase 1 deliverable, generated by `src/profile.py` from the `profile_*` "
        "tables and `reports/metrics.json`. Nothing here is typed by hand except "
        "the problems list in section 4.",
        "",
        f"- Rows profiled: **{_count(row_count)}**",
        f"- Columns profiled: **{metrics['profile.profiled_column_count']}** — the ten Febrl "
        "fields plus the two synthetic metadata columns. The surrogate key, the source "
        "record identifier and the ground-truth label are excluded: the key is generated "
        "during ingest and says nothing about quality, and the other two are ground truth "
        "that no stage after ingest may read (AGENTS.md hard rule 1).",
        "- A value that is NULL, empty, or only whitespace counts as missing.",
        "",
        "## 1. Completeness and cardinality",
        "",
    ]

    summary_rows = []
    for row in columns_frame.itertuples(index=False):
        summary_rows.append(
            [
                f"`{row.column_name}`",
                _count(row.populated_count),
                _percent(row.completeness_rate),
                _count(row.null_count),
                _count(row.empty_count),
                _count(row.distinct_count),
                _count(row.min_length),
                _count(row.max_length),
                _count(row.distinct_pattern_count),
            ]
        )
    parts.append(
        _md_table(
            [
                "Column",
                "Populated",
                "Complete",
                "NULL",
                "Empty/blank",
                "Distinct",
                "Min len",
                "Max len",
                "Distinct patterns",
            ],
            summary_rows,
        )
    )

    parts += [
        "",
        "## 2. Ground-truth duplication",
        "",
        "Measured from `ground_truth_cluster_sizes`, an aggregate written during "
        "ingest. It holds counts per cluster size only, so this stage can report how "
        "duplicated the data is without being able to see which records belong "
        "together — that stays with ingest and evaluation.",
        "",
        f"- Records: **{_count(metrics['profile.ground_truth.record_count'])}**",
        f"- True entities: **{_count(metrics['profile.ground_truth.entity_count'])}**",
        "- Records per entity (the duplicate rate): "
        f"**{metrics['profile.ground_truth.records_per_entity']:.3f}**",
        "- Records beyond one per entity: "
        f"**{_count(metrics['profile.ground_truth.redundant_record_count'])}**",
        "- Cluster size range: "
        f"**{metrics['profile.ground_truth.min_cluster_size']}**–"
        f"**{metrics['profile.ground_truth.max_cluster_size']}** records per entity",
        "",
    ]

    cluster_rows = [
        [
            _count(row.cluster_size),
            _count(row.entity_count),
            _percent(row.entity_share),
            _count(row.record_count),
            _percent(row.record_share),
        ]
        for row in clusters_frame.itertuples(index=False)
    ]
    parts.append(
        _md_table(
            ["Records in entity", "Entities", "Share of entities", "Records", "Share of records"],
            cluster_rows,
        )
    )

    parts += [
        "",
        "## 3. Values and format patterns, per column",
        "",
        "Patterns map every digit to `9` and every letter to `A`, leaving separators "
        "alone, so a column holding one format shows one pattern and format drift shows "
        "as several. Because that encodes length as well, a second view collapses runs "
        "of one symbol: `1942-08-04` becomes `9-9-9` and `mary-jane` becomes `A-A`. The "
        "pattern view answers \"are the lengths consistent?\" and the shape view answers "
        "\"are the separators consistent?\". Missing values are excluded from these "
        "tables; their counts are in section 1.",
        "",
    ]

    for row in columns_frame.itertuples(index=False):
        column = row.column_name
        parts += [
            f"### `{column}`",
            "",
            f"{_count(row.distinct_count)} distinct values across "
            f"{_count(row.populated_count)} populated rows, in "
            f"{_count(row.distinct_pattern_count)} distinct pattern(s) and "
            f"{_count(row.distinct_shape_count)} distinct shape(s).",
            "",
            f"**Top {TOP_N_VALUES} values**",
            "",
        ]
        value_rows = [
            [_count(v.rank), _code_cell(v.value), _count(v.frequency), _percent(v.frequency / row_count)]
            for v in top_values_frame[top_values_frame["column_name"] == column].itertuples(index=False)
        ]
        parts.append(_md_table(["#", "Value", "Rows", "Share of rows"], value_rows))
        for kind, heading in (("pattern", "patterns"), ("shape", "shapes")):
            selected = patterns_frame[
                (patterns_frame["column_name"] == column) & (patterns_frame["kind"] == kind)
            ]
            parts += ["", f"**Top {TOP_N_PATTERNS} {heading}**", ""]
            pattern_rows = [
                [
                    _count(p.rank),
                    _code_cell(p.pattern),
                    _count(p.frequency),
                    _percent(p.frequency / row_count),
                ]
                for p in selected.itertuples(index=False)
            ]
            parts.append(
                _md_table(["#", heading[:-1].title(), "Rows", "Share of rows"], pattern_rows)
            )
        parts.append("")

    parts += [
        "## 4. Problems observed",
        "",
        "Owner-written (roadmap section 10.1): this is the judgement call the rest of "
        "the phase exists to support, and it becomes the Phase 2 rule list. Text between "
        "the markers below survives regeneration of this report.",
        "",
        PROBLEMS_START,
        problems if problems else PROBLEMS_PLACEHOLDER,
        PROBLEMS_END,
        "",
    ]
    return "\n".join(parts)


def write_report(text: str, path: Path | None = None) -> Path:
    """Write the rendered report, creating `reports/` if it is missing."""
    path = Path(path) if path is not None else REPORT_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def run(
    db_path: Path | str = DEFAULT_DB_PATH,
    report_path: Path | str | None = None,
    metrics_path: Path | str | None = None,
) -> dict:
    """Profile `raw_customers`, write the `profile_*` tables and the report.

    Reads only; the four tables it creates are this stage's own output, replaced
    on each run so the database matches the report beside it.
    """
    report_path = Path(report_path) if report_path is not None else REPORT_PATH

    with duckdb.connect(str(db_path)) as con:
        con.execute(f"CREATE OR REPLACE TABLE {COLUMN_TABLE} AS {column_stats_sql()}")
        con.execute(f"CREATE OR REPLACE TABLE {TOP_VALUE_TABLE} AS {top_values_sql()}")
        con.execute(f"CREATE OR REPLACE TABLE {PATTERN_TABLE} AS {top_patterns_sql()}")
        con.execute(f"CREATE OR REPLACE TABLE {CLUSTER_PROFILE_TABLE} AS {cluster_size_sql()}")

        columns_frame = con.execute(f"SELECT * FROM {COLUMN_TABLE}").fetch_df()
        top_values_frame = con.execute(f"SELECT * FROM {TOP_VALUE_TABLE}").fetch_df()
        patterns_frame = con.execute(f"SELECT * FROM {PATTERN_TABLE}").fetch_df()
        clusters_frame = con.execute(
            f"SELECT * FROM {CLUSTER_PROFILE_TABLE} ORDER BY cluster_size"
        ).fetch_df()

    columns_frame = sort_by_column_order(columns_frame)
    top_values_frame = sort_by_column_order(top_values_frame, "rank")
    patterns_frame = sort_by_column_order(patterns_frame, "kind", "rank")

    metrics = build_metrics(columns_frame, clusters_frame)
    ingest.write_metrics(metrics, metrics_path)

    report = render_report(
        metrics,
        columns_frame,
        top_values_frame,
        patterns_frame,
        clusters_frame,
        problems=existing_problems_section(report_path),
    )
    write_report(report, report_path)
    return metrics


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default=str(DEFAULT_DB_PATH), help="path to the DuckDB file")
    parser.add_argument("--report", default=None, help="path for the generated profile.md")
    args = parser.parse_args()

    metrics = run(args.db, report_path=args.report)
    for key, value in metrics.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
