"""
Tests for OdooRestAPI route collection.

Note: register() requires Odoo's http.Controller and is not tested here.
Only the decorator-based route collection is tested.
"""

import pytest

from odoo_rest_api.api import OdooRestAPI, RouteDefinition


class TestRouteDefinition:
    def test_defaults(self):
        def dummy():
            pass

        rd = RouteDefinition(method="GET", path="/test", handler=dummy)
        assert rd.auth == "none"
        assert rd.cors == "*"

    def test_simple_error_default(self):
        api = OdooRestAPI(prefix="/api/v1")
        assert api.simple_error is False

    def test_simple_error_enabled(self):
        api = OdooRestAPI(prefix="/api/v1", simple_error=True)
        assert api.simple_error is True


class TestOdooRestAPIRouteCollection:
    def setup_method(self):
        self.api = OdooRestAPI(prefix="/api/v1")

    def test_get_decorator(self):
        @self.api.get("/partners")
        def list_partners(env):
            pass

        assert len(self.api.routes) == 1
        assert self.api.routes[0].method == "GET"
        assert self.api.routes[0].path == "/api/v1/partners"
        assert self.api.routes[0].handler is list_partners

    def test_post_decorator(self):
        @self.api.post("/partners")
        def create_partner(env, body):
            pass

        assert self.api.routes[0].method == "POST"

    def test_put_decorator(self):
        @self.api.put("/partners/{id}")
        def update_partner(env, id, body):
            pass

        assert self.api.routes[0].method == "PUT"
        assert self.api.routes[0].path == "/api/v1/partners/{id}"

    def test_patch_decorator(self):
        @self.api.patch("/partners/{id}")
        def patch_partner(env, id, body):
            pass

        assert self.api.routes[0].method == "PATCH"

    def test_delete_decorator(self):
        @self.api.delete("/partners/{id}")
        def delete_partner(env, id):
            pass

        assert self.api.routes[0].method == "DELETE"

    def test_multiple_routes(self):
        @self.api.get("/partners")
        def list_partners(env):
            pass

        @self.api.post("/partners")
        def create_partner(env, body):
            pass

        @self.api.get("/partners/{id}")
        def get_partner(env, id):
            pass

        assert len(self.api.routes) == 3
        assert self.api.routes[0].method == "GET"
        assert self.api.routes[1].method == "POST"
        assert self.api.routes[2].path == "/api/v1/partners/{id}"

    def test_decorator_returns_original_function(self):
        @self.api.get("/partners")
        def list_partners(env):
            return "original"

        # The decorator should not wrap the function
        assert list_partners(None) == "original"

    def test_prefix_stripping(self):
        api = OdooRestAPI(prefix="/api/v1/")
        assert api.prefix == "/api/v1"

    def test_empty_prefix(self):
        api = OdooRestAPI()

        @api.get("/health")
        def health(env):
            pass

        assert api.routes[0].path == "/health"

    def test_custom_auth_per_route(self):
        @self.api.get("/public", auth="none")
        def public_route(env):
            pass

        @self.api.get("/private", auth="api_key")
        def private_route(env):
            pass

        assert self.api.routes[0].auth == "none"
        assert self.api.routes[1].auth == "api_key"

    def test_default_auth(self):
        api = OdooRestAPI(prefix="/api", auth="jwt")

        @api.get("/test")
        def test_route(env):
            pass

        assert api.routes[0].auth == "jwt"

    def test_custom_cors_per_route(self):
        @self.api.get("/test", cors="https://example.com")
        def test_route(env):
            pass

        assert self.api.routes[0].cors == "https://example.com"

    def test_unknown_option_is_rejected(self):
        with pytest.raises(TypeError):
            self.api.get("/partners", tag="typo")


class TestRouteOverriding:
    def setup_method(self):
        self.api = OdooRestAPI(prefix="/api/v1")

    def test_override_same_path_and_method(self):
        @self.api.get("/partners")
        def list_partners_v1(env):
            return "v1"

        @self.api.get("/partners")
        def list_partners_v2(env):
            return "v2"

        # Should replace, not append
        assert len(self.api.routes) == 1
        assert self.api.routes[0].handler is list_partners_v2

    def test_different_method_same_path_not_overridden(self):
        @self.api.get("/partners")
        def list_partners(env):
            pass

        @self.api.post("/partners")
        def create_partner(env, body):
            pass

        # GET and POST on same path are separate routes
        assert len(self.api.routes) == 2

    def test_different_path_same_method_not_overridden(self):
        @self.api.get("/partners")
        def list_partners(env):
            pass

        @self.api.get("/orders")
        def list_orders(env):
            pass

        assert len(self.api.routes) == 2

    def test_override_preserves_position(self):
        @self.api.get("/partners")
        def list_partners(env):
            pass

        @self.api.get("/orders")
        def list_orders(env):
            pass

        @self.api.get("/partners")
        def list_partners_v2(env):
            pass

        # Override should keep the original position (index 0)
        assert len(self.api.routes) == 2
        assert self.api.routes[0].handler is list_partners_v2
        assert self.api.routes[1].handler is list_orders

    def test_override_updates_auth(self):
        @self.api.get("/partners", auth="none")
        def list_partners(env):
            pass

        @self.api.get("/partners", auth="api_key")
        def list_partners_secure(env):
            pass

        assert len(self.api.routes) == 1
        assert self.api.routes[0].auth == "api_key"
        assert self.api.routes[0].handler is list_partners_secure

    def test_override_updates_tags(self):
        @self.api.get("/partners", tags=["v1"])
        def list_partners(env):
            pass

        @self.api.get("/partners", tags=["v2", "CRM"])
        def list_partners_v2(env):
            pass

        assert self.api.routes[0].tags == ["v2", "CRM"]

    def test_override_returns_original_function(self):
        @self.api.get("/partners")
        def list_partners(env):
            return "v1"

        @self.api.get("/partners")
        def list_partners_v2(env):
            return "v2"

        # Decorator still returns the original function
        assert list_partners_v2(None) == "v2"


class TestRoutePriority:
    def setup_method(self):
        self.api = OdooRestAPI(prefix="/api/v1")

    def test_higher_priority_wins(self):
        @self.api.get("/partners", priority=0)
        def list_partners_base(env):
            return "base"

        @self.api.get("/partners", priority=10)
        def list_partners_custom(env):
            return "custom"

        assert len(self.api.routes) == 1
        assert self.api.routes[0].handler is list_partners_custom
        assert self.api.routes[0].priority == 10

    def test_lower_priority_does_not_override(self):
        @self.api.get("/partners", priority=10)
        def list_partners_custom(env):
            return "custom"

        @self.api.get("/partners", priority=5)
        def list_partners_base(env):
            return "base"

        assert len(self.api.routes) == 1
        assert self.api.routes[0].handler is list_partners_custom

    def test_equal_priority_last_wins(self):
        @self.api.get("/partners", priority=5)
        def list_partners_v1(env):
            return "v1"

        @self.api.get("/partners", priority=5)
        def list_partners_v2(env):
            return "v2"

        assert len(self.api.routes) == 1
        assert self.api.routes[0].handler is list_partners_v2

    def test_default_priority_is_zero(self):
        @self.api.get("/partners")
        def list_partners(env):
            pass

        assert self.api.routes[0].priority == 0

    def test_priority_independent_per_path(self):
        @self.api.get("/partners", priority=10)
        def list_partners(env):
            pass

        @self.api.get("/orders", priority=5)
        def list_orders(env):
            pass

        assert len(self.api.routes) == 2
        assert self.api.routes[0].priority == 10
        assert self.api.routes[1].priority == 5

    def test_priority_preserves_position(self):
        @self.api.get("/partners")
        def list_partners(env):
            pass

        @self.api.get("/orders")
        def list_orders(env):
            pass

        @self.api.get("/partners", priority=10)
        def list_partners_custom(env):
            pass

        assert len(self.api.routes) == 2
        assert self.api.routes[0].handler is list_partners_custom
        assert self.api.routes[1].handler is list_orders
