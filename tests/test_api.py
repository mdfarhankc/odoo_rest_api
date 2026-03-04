"""
Tests for OdooRestAPI route collection.

Note: register() requires Odoo's http.Controller and is not tested here.
Only the decorator-based route collection is tested.
"""

from odoo_rest_api.api import OdooRestAPI, RouteDefinition


class TestRouteDefinition:
    def test_defaults(self):
        def dummy():
            pass

        rd = RouteDefinition(method="GET", path="/test", handler=dummy)
        assert rd.auth == "none"
        assert rd.cors == "*"


class TestOdooRestAPIRouteCollection:
    def setup_method(self):
        # Clear class-level instances to avoid pollution between tests
        OdooRestAPI._instances = []
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

    def test_instances_tracked(self):
        OdooRestAPI._instances = []
        api1 = OdooRestAPI(prefix="/api/v1")
        api2 = OdooRestAPI(prefix="/api/v2")
        assert len(OdooRestAPI._instances) == 2
        assert OdooRestAPI._instances[0] is api1
        assert OdooRestAPI._instances[1] is api2
