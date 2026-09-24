"""Release hygiene: one version everywhere."""

import re
from pathlib import Path

import asciicharts

ROOT = Path(__file__).resolve().parent.parent


def test_versions_agree():
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    declared = re.search(r'^version = "([^"]+)"', pyproject, re.M).group(1)
    assert asciicharts.__version__ == declared
    assert re.fullmatch(r"\d+\.\d+\.\d+", declared)


def test_package_name():
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert re.search(r'^name = "asciicharts"$', pyproject, re.M)
