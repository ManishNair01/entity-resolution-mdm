"""Invariant tests for `ingest.py`: rules the output must obey for *any* seed.

The reproducibility tests prove the pipeline is consistent (same input, same
output). They cannot prove it is correct: a bug such as dropping the `- 1` in the
`last_updated` window would be reproduced identically on every run and pass them.
These tests pin down properties instead of specific values, so they survive a
change of `RANDOM_SEED` but fail if the logic drifts.
"""

from datetime import date, timedelta

import pandas as pd
import pytest

from src import ingest

# Written out independently of ingest.py's own arithmetic on purpose: if the test
# reused the module's formula, a bug in that formula would pass its own test.
WINDOW_END = date(2026, 9, 22)
WINDOW_START = WINDOW_END - timedelta(days=3 * 365 - 1)  # 2023-09-24, inclusive


@pytest.fixture(scope="module", params=[ingest.RANDOM_SEED, 7], ids=["seed42", "seed7"])
def frame(request) -> pd.DataFrame:
    """Build the table in memory for two seeds: the invariants must hold for both."""
    return ingest.build_raw_customers(seed=request.param)


def test_window_constant_is_what_the_test_assumes():
    assert WINDOW_START == date(2023, 9, 24)


def test_last_updated_inside_window(frame):
    dates = pd.to_datetime(frame["last_updated"]).dt.date
    assert dates.min() >= WINDOW_START, f"date before window: {dates.min()}"
    assert dates.max() <= WINDOW_END, f"date after window: {dates.max()}"


def test_source_system_uses_exactly_the_three_systems(frame):
    assert set(frame["source_system"]) == {"CRM", "ERP", "WEB_FORM"}


def test_unique_id_is_a_permutation_of_row_numbers(frame):
    assert sorted(frame["unique_id"]) == list(range(len(frame)))


def test_unique_id_does_not_follow_rec_id_order(frame):
    """Leakage check: IDs handed out in rec_id order would group each entity's records."""
    in_rec_id_order = frame.sort_values("rec_id")["unique_id"].tolist()
    assert in_rec_id_order != sorted(in_rec_id_order)


def test_ground_truth_is_seed_independent():
    """The seed may move metadata around, but never the answer key or the Febrl fields."""
    cols = ["rec_id", "true_cluster_id", *ingest.FEBRL_COLUMNS]
    a = ingest.build_raw_customers(seed=42)[cols].sort_values("rec_id").reset_index(drop=True)
    b = ingest.build_raw_customers(seed=7)[cols].sort_values("rec_id").reset_index(drop=True)
    pd.testing.assert_frame_equal(a, b)
