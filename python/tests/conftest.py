import pytest

try:
    import asciicharts  # noqa: F401
except ImportError:  # pragma: no cover
    pytest.exit("asciicharts is not importable: install the project first, "
                "e.g. `pip install -e \"./python[dev]\"` from the repository root", returncode=2)
