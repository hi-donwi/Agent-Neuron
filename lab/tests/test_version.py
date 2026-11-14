import json
import platform
import tomllib
from pathlib import Path

import pytest

import neuron_lab
from neuron_lab.__main__ import main

PYPROJECT = Path(__file__).resolve().parents[1] / "pyproject.toml"


def declared_version() -> str:
    return tomllib.loads(PYPROJECT.read_text())["project"]["version"]


def test_package_version_is_the_one_declared_in_pyproject():
    assert neuron_lab.__version__ == declared_version()


def test_version_prints_one_human_readable_line(capsys):
    assert main(["version"]) == 0

    out = capsys.readouterr().out
    assert out == f"neuron-lab {declared_version()} (python {platform.python_version()})\n"


def test_version_json_has_exactly_the_documented_keys(capsys):
    assert main(["version", "--json"]) == 0

    info = json.loads(capsys.readouterr().out)
    assert info == {"version": declared_version(), "python": platform.python_version()}


def test_a_missing_command_fails(capsys):
    with pytest.raises(SystemExit) as exit_info:
        main([])

    assert exit_info.value.code == 2


def test_an_unknown_command_fails(capsys):
    with pytest.raises(SystemExit) as exit_info:
        main(["no-such-command"])

    assert exit_info.value.code == 2
