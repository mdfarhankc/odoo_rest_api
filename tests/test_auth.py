"""
Tests for the pluggable auth handler registry.

Note: validate_request() and get_authenticated_env() require Odoo and
are not tested here. Only the registry mechanism is tested.
"""

import pytest

from odoo_rest_api.auth import (
    _auth_handlers,
    get_auth_handler,
    register_auth_handler,
)


class TestAuthHandlerRegistry:
    def setup_method(self):
        # Clear the registry between tests
        _auth_handlers.clear()

    def test_register_and_get(self):
        def my_handler(request):
            return 1

        register_auth_handler("test_key", my_handler)
        assert get_auth_handler("test_key") is my_handler

    def test_get_unregistered_returns_none(self):
        assert get_auth_handler("nonexistent") is None

    def test_override_handler(self):
        def handler_v1(request):
            return 1

        def handler_v2(request):
            return 2

        register_auth_handler("key", handler_v1)
        register_auth_handler("key", handler_v2)
        assert get_auth_handler("key") is handler_v2

    def test_multiple_handlers(self):
        def api_key_handler(request):
            return 1

        def jwt_handler(request):
            return 2

        register_auth_handler("api_key", api_key_handler)
        register_auth_handler("jwt", jwt_handler)

        assert get_auth_handler("api_key") is api_key_handler
        assert get_auth_handler("jwt") is jwt_handler
