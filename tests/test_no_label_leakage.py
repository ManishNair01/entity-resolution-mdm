"""Guard test: ground truth must not reach the matching code (AGENTS.md hard rule 1).

Only `ingest.py` (which creates the label) and `evaluate.py` (which uses it to
score results) may mention `true_cluster_id`. Any other module touching it means
the model could be trained or tuned on the answers.
"""

from pathlib import Path

import pytest

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
ALLOWED_FILES = {"ingest.py", "evaluate.py"}
FORBIDDEN_STRING = "true_cluster_id"


def src_modules() -> list[Path]:
    return sorted(p for p in SRC_DIR.rglob("*.py") if p.name not in ALLOWED_FILES)


def test_src_directory_exists():
    assert SRC_DIR.is_dir(), f"expected source directory at {SRC_DIR}"


@pytest.mark.parametrize("module_path", src_modules(), ids=lambda p: p.name)
def test_module_does_not_reference_ground_truth(module_path: Path):
    text = module_path.read_text(encoding="utf-8")
    offending = [
        f"line {n}: {line.strip()}"
        for n, line in enumerate(text.splitlines(), start=1)
        if FORBIDDEN_STRING in line
    ]
    assert not offending, (
        f"{module_path.name} references {FORBIDDEN_STRING!r}, which is label leakage.\n"
        + "\n".join(offending)
    )
