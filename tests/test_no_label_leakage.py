"""Guard test: ground truth must not reach the matching code (AGENTS.md hard rule 1).

Ground truth is both `true_cluster_id` and `rec_id`: a value like `rec-12-dup-0`
spells out the entity number just as plainly as the label does. Only `ingest.py`
(which creates them) and `evaluate.py` (which uses them to score results) may
mention either. Any other module touching one means the model could be trained,
tuned or chosen on the answers instead of doing real matching.
"""

from pathlib import Path

import pytest

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
ALLOWED_FILES = {"ingest.py", "evaluate.py"}
FORBIDDEN_STRINGS = ("true_cluster_id", "rec_id")


def src_modules() -> list[Path]:
    return sorted(p for p in SRC_DIR.rglob("*.py") if p.name not in ALLOWED_FILES)


def test_src_directory_exists():
    assert SRC_DIR.is_dir(), f"expected source directory at {SRC_DIR}"


@pytest.mark.parametrize("module_path", src_modules(), ids=lambda p: p.name)
def test_module_does_not_reference_ground_truth(module_path: Path):
    text = module_path.read_text(encoding="utf-8")
    offending = [
        f"line {n}: {forbidden!r} in: {line.strip()}"
        for n, line in enumerate(text.splitlines(), start=1)
        for forbidden in FORBIDDEN_STRINGS
        if forbidden in line
    ]
    assert not offending, (
        f"{module_path.name} references ground truth "
        f"({' or '.join(repr(s) for s in FORBIDDEN_STRINGS)}), which is label leakage.\n"
        + "\n".join(offending)
    )
