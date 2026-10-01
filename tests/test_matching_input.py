"""Matching input preserves earlier stages and excludes invalid evidence."""
import duckdb
import pytest
import yaml

from src import baseline, blocking, ingest, matching_input


@pytest.fixture
def fixture_db(tmp_path, monkeypatch):
    monkeypatch.setattr(ingest, 'METRICS_PATH', tmp_path / 'metrics.json')
    db = tmp_path / 'matching.duckdb'
    config = tmp_path / 'dq.yaml'
    config.write_text(yaml.safe_dump({'standardization': [
        {'field': 'postcode', 'steps': [{'type': 'trim'}]},
        {'field': 'soc_sec_id', 'steps': [{'type': 'trim'}]},
    ]}))
    with duckdb.connect(str(db)) as con:
        con.execute('CREATE TABLE std_customers (unique_id INT, postcode_std VARCHAR, soc_sec_id_std VARCHAR, true_cluster_id INT, rec_id VARCHAR)')
        con.execute("INSERT INTO std_customers VALUES (1, '20A0', '1234567', 1, 'label-1'), (2, '20A0', '1234567', 1, 'label-2'), (3, '2000', NULL, 2, 'label-3')")
        con.execute('CREATE TABLE dq_violations_std (unique_id INT, field VARCHAR, dimension VARCHAR)')
        # Duplicated validity flags must not duplicate records. Completeness must not drop a record.
        con.execute("INSERT INTO dq_violations_std VALUES (1, 'postcode_std', 'validity'), (1, 'postcode_std', 'validity'), (2, 'postcode_std', 'validity'), (3, 'identity_evidence', 'completeness')")
    return db, config


def test_masking_preserves_sources_and_records(fixture_db):
    db, config = fixture_db
    with duckdb.connect(str(db)) as con:
        before = con.execute('SELECT * FROM std_customers ORDER BY unique_id').fetchall()
        flags = con.execute('SELECT * FROM dq_violations_std ORDER BY ALL').fetchall()
    first = matching_input.run(db, config)
    assert first['matching_input.masked_values_by_field'] == {'postcode_std': 2, 'soc_sec_id_std': 0}
    assert first == matching_input.run(db, config)
    with duckdb.connect(str(db)) as con:
        assert con.execute('SELECT * FROM std_customers ORDER BY unique_id').fetchall() == before
        assert con.execute('SELECT * FROM dq_violations_std ORDER BY ALL').fetchall() == flags
        assert [r[0] for r in con.execute('DESCRIBE matching_customers').fetchall()] == ['unique_id', 'postcode_std', 'soc_sec_id_std']
        assert con.execute('SELECT * FROM matching_customers ORDER BY unique_id').fetchall() == [(1, None, '1234567'), (2, None, '1234567'), (3, '2000', None)]


def test_both_matchers_use_masked_input(fixture_db, tmp_path):
    db, config = fixture_db
    matching_input.run(db, config)
    base = tmp_path / 'baseline.yaml'
    base.write_text(yaml.safe_dump({'variants': [{'id': 'postcode', 'description': 'test', 'match_on': ['postcode_std']}]}))
    block = tmp_path / 'blocking.yaml'
    block.write_text(yaml.safe_dump({'rules': [
        {'id': 'postcode', 'description': 'test', 'keys': ['postcode_std']},
        {'id': 'identifier', 'description': 'test', 'keys': ['soc_sec_id_std']},
    ]}))
    result = baseline.run(db, base, source_table=matching_input.TABLE_NAME)
    assert result['baseline.matched_pairs_by_variant'] == {'postcode': 0}
    result = blocking.run(db, block, source_table=matching_input.TABLE_NAME)
    assert result['blocking.candidate_pairs_by_rule'] == {'postcode': 0, 'identifier': 1}
    assert result['blocking.record_count'] == 3
    # Reintroducing a flagged value is still rejected; masking cannot bypass the guard.
    with duckdb.connect(str(db)) as con:
        con.execute("UPDATE matching_customers SET postcode_std = '20A0' WHERE unique_id = 1")
    with pytest.raises(ValueError, match='flagged invalid'):
        baseline.run(db, base, source_table=matching_input.TABLE_NAME)


def test_missing_dq_output_refused(fixture_db):
    db, config = fixture_db
    with duckdb.connect(str(db)) as con:
        con.execute('DROP TABLE dq_violations_std')
    with pytest.raises(ValueError, match='dq_std'):
        matching_input.run(db, config)
