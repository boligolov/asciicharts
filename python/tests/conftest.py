import pytest

try:
    import asciicharts_server  # noqa: F401
except ImportError:  # pragma: no cover
    pytest.exit("asciicharts_server is not importable: install the project first, "
                "e.g. `pip install -e \"./python[stats,dev]\"` from the repository root", returncode=2)
