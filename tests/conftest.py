import pytest

try:
    import asciicharts_server  # noqa: F401
except ImportError:  # pragma: no cover
    pytest.exit("asciicharts_server is not importable: install the project first, "
                "e.g. `pip install -e \".[stats,dev]\"`", returncode=2)
