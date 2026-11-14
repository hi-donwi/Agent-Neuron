import hashlib
from pathlib import Path

import pytest

EVALS = Path(__file__).resolve().parents[2] / "evals"
MANIFESTS = sorted(EVALS.glob("**/SHA256SUMS"))


def frozen_files():
    files = []
    for manifest in MANIFESTS:
        for line in manifest.read_text(encoding="utf-8").splitlines():
            expected, _, name = line.partition("  ")
            files.append(pytest.param(manifest.parent / name, expected, id=name))
    return files


def test_there_is_at_least_one_frozen_evaluation_set():
    assert MANIFESTS


@pytest.mark.parametrize(("path", "expected"), frozen_files())
def test_a_frozen_evaluation_set_has_not_changed(path, expected):
    assert hashlib.sha256(path.read_bytes()).hexdigest() == expected
