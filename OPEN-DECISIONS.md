# Open decisions

Things the agent needs from the owner, and the decisions already made. The agent
adds to this file whenever it hits a choice that belongs to the owner
(`AGENTS.md`, "Owner-owned decisions"), or makes an assumption to keep moving.

**Owner:** Manish Manoj Nair · **Last updated:** 2026-09-27 (all Phase 0–1 decisions closed; problems list moved to its own file)

- **Open** — waiting on you. The agent has assumed something in the meantime;
  each entry says what.
- **Decided** — settled. Kept so the reasoning survives, because interview
  questions come from this list.

---

## Open

Nothing open.

---

## Needed before the next phase

**Phase 2 — DQ rules.** The owner writes every rule in `config/dq_rules.yaml` and decides the mandatory fields, starting from the "Problems observed" list (P1–P8) in `reports/profile.md`.

---

## Decided

| Date | Decision | Notes |
|---|---|---|
| 2026-09-22 | Python 3.11 via `py -3.11`; venv at `.venv` | The machine's default `python` is 3.9 |
| 2026-09-22 | Repo `entity-resolution-mdm`, public, MIT | Description and topics set in the GitHub UI |
| 2026-09-22 | Derive synthetic values by hash, not RNG | Makes the fresh-clone test reproducible across platforms, Python versions and input order |
| 2026-09-22 | `unique_id` = rank of a hash of `rec_id` | Sequential IDs in `rec_id` order would have leaked the entity through the key itself |
| 2026-09-22 | Commit the reports, ignore `reports/metrics.json` only | `profile.md` and the scorecard are deliverables; the metrics file churns every run |
| 2026-09-22 | Synthetic `source_system` and `last_updated` | Roadmap §2. Uniform over CRM / ERP / WEB_FORM and over the 3 years to 2026-09-22; documented as synthetic in the README |
| 2026-09-23 | No second issue tracker: reverted the GitHub-issues / triage-label / ADR skill setup | `AGENTS.md` and `OPEN-DECISIONS.md` already carry the decisions for a solo, single-repo project; the setup duplicated that ledger and was out of phase. Don't re-run it. |
| 2026-09-23 | The leakage guard covers `rec_id` as well as `true_cluster_id` | `rec-12-dup-0` names the entity as plainly as the label does, so leaving it unguarded would let the matching code cheat instead of matching. `AGENTS.md` rule 1 and `tests/test_no_label_leakage.py` now cover both strings; `ingest.py` and `evaluate.py` stay exempt |
| 2026-09-26 | Accept `ingest.cluster_size_distribution` in `ingest.py` | Only ingest/evaluate may group by ground truth (rule 1); profile.py reads it back from metrics.json |
| 2026-09-26 | "Duplicate rate" = duplicate records ÷ total records; "average records per entity" = records ÷ entities | Standard DQ meaning; both reported, under separate names |
| 2026-09-26 | Record-ID format confirmed: `rec-<N>-org` / `rec-<N>-dup-<k>`, `<N>` = entity | Verified by owner in DuckDB: 5,000 rows / 2,000 entities; 0 IDs outside the pattern in the raw CSV; exactly one `-org` per entity; `true_cluster_id` matches `<N>` in all rows |
| 2026-09-27 | Dependency pins accepted as installed on 2026-09-22 | `pandas==2.3.3`, `duckdb==1.5.5`, `splink==4.0.17`, `recordlinkage==0.16`, `PyYAML==6.0.3`, `pytest==9.1.1`. Splink v4 API only |
| 2026-09-27 | Ingest constants (`RANDOM_SEED`, `LAST_UPDATED_REFERENCE_DATE`, 3-year window) stay in `src/ingest.py` | They aren't DQ, blocking or survivorship rules, which is what the config rule covers |
| 2026-09-27 | Keep `data/raw/febrl3.csv` tracked in git | Makes the input inspectable on GitHub; `.gitattributes` keeps it byte-identical across clones |
| 2026-09-27 | One pull request per phase | Gives a diff to review against the roadmap §10.4 checklist |
| 2026-09-27 | The problems list lives in `reports/problems_observed.md`; `profile.py` embeds it verbatim at the end of `profile.md` | `profile.md` is regenerated on every run, so any hand edit to it was lost. The owner edits only the separate file; the generated report still has the "Problems observed" section the roadmap §5 deliverable asks for. `[TBD]` if the file is missing |

---

## Assumptions recorded in code

Each is a decision the agent made to keep moving. Overrule any of them.

- Source systems are drawn uniformly, so the three systems hold roughly a third
  of the records each. Real systems are rarely balanced; if you want the
  survivorship story in Phase 6 to be more realistic, an uneven split would
  reflect that better.
- `last_updated` is uniform over the 3 years to `LAST_UPDATED_REFERENCE_DATE`,
  with no correlation to `source_system` or to whether a record is an original
  or a duplicate.
- `reports/metrics.json` keys are namespaced by stage, e.g. `ingest.record_count`.
