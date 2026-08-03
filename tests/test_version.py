"""
Tests for package version resolution and the declared public surface.
"""

from importlib.metadata import version as get_version

import odoo_rest_api


def test_version_resolves_from_distribution_metadata():
    """__version__ comes from installed metadata, not a hardcoded literal.

    Guards against a typo in the distribution name passed to importlib.metadata,
    which would silently fall back to the dev placeholder.
    """
    assert odoo_rest_api.__version__ == get_version("odoo-rest-api")
    assert odoo_rest_api.__version__ != "0.0.0.dev0"


def test_all_names_are_importable():
    for name in odoo_rest_api.__all__:
        assert hasattr(odoo_rest_api, name), f"__all__ lists missing name: {name}"
