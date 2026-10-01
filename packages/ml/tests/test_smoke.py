"""Smoke test: the package imports and exposes a version (CP-01)."""

import pytest

import cocok_ml


@pytest.mark.cp01
def test_package_imports_and_has_version() -> None:
    assert cocok_ml.__version__ == "0.1.0"
