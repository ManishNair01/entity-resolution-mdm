# Entity Resolution and Golden-Record Pipeline

Customer records entered by different people, at different times, in different
systems: the same person appears several times with typos, missing fields, and
inconsistent formatting. This project measures how bad the data is, finds the
records that refer to the same person, and merges each group into one trusted
**golden record** built by explicit, documented rules — the core loop of Master
Data Management.

Built on [Febrl 3](https://recordlinkage.readthedocs.io/) (5,000 synthetic
Australian person records over 2,000 true entities), with
[Splink](https://moj-analytical-services.github.io/splink/) for probabilistic
matching and DuckDB for storage.

> **Status: work in progress — Phase 1 of 7.** This README is a placeholder.
> Results, the approach diagram, and limitations land in Phase 7. The plan is in
> [`project-1-entity-resolution-roadmap.md`](project-1-entity-resolution-roadmap.md);
> every rule will be written in plain English in `RULEBOOK.md`.

## Results

[TBD] — no numbers are published until the pipeline has measured them. The data
profile produced so far is in [`reports/profile.md`](reports/profile.md).

## How to run

```bash
python -m venv .venv
pip install -r requirements.txt
python run_pipeline.py    # raw data -> scorecard
pytest                    # unit tests and guard tests
```

Requires Python 3.11+. Every stage reads from `data/mdm.duckdb` and writes a new
table, so each step is inspectable and the whole run is reproducible from a fixed
seed.

## Notes on the data

Febrl 3 is synthetic, and it carries no source system or timestamp. The
`source_system` and `last_updated` columns this pipeline uses for survivorship
are generated, not real — see `src/ingest.py`.
