"""Tests for OpenAPI spec generation."""

from odoo_rest_api.api import OdooRestAPI, RouteDefinition
from odoo_rest_api.docs import (
    generate_openapi_spec,
    get_swagger_ui_html,
    _parse_docstring,
    _get_tag,
    _extract_path_params,
    _python_type_to_openapi,
)


# ── Helper factories ─────────────────────────────────────────────


def _make_api(**kwargs):
    defaults = dict(prefix="/api/v1", docs=True, title="Test API", version="0.1.0")
    defaults.update(kwargs)
    return OdooRestAPI(**defaults)


# ── Unit tests ───────────────────────────────────────────────────


class TestParseDocstring:
    def test_full_docstring(self):
        def handler():
            """Get all partners.

            Returns a paginated list of partners.
            Supports filtering by name.
            """

        summary, desc = _parse_docstring(handler)
        assert summary == "Get all partners."
        assert "paginated list" in desc

    def test_single_line(self):
        def handler():
            """Get a partner by ID."""

        summary, desc = _parse_docstring(handler)
        assert summary == "Get a partner by ID."
        assert desc == ""

    def test_no_docstring(self):
        def handler():
            pass

        summary, desc = _parse_docstring(handler)
        assert summary == ""
        assert desc == ""


class TestGetTag:
    def test_module_tag(self):
        def handler():
            pass

        handler.__module__ = "my_addon.controllers.partner"
        rd = RouteDefinition(method="GET", path="/partners", handler=handler)
        assert _get_tag(rd) == "partner"

    def test_init_module(self):
        def handler():
            pass

        handler.__module__ = "my_addon.controllers.__init__"
        rd = RouteDefinition(method="GET", path="/partners", handler=handler)
        assert _get_tag(rd) == "controllers"

    def test_no_module(self):
        def handler():
            pass

        handler.__module__ = ""
        rd = RouteDefinition(method="GET", path="/partners", handler=handler)
        assert _get_tag(rd) == "default"


class TestExtractPathParams:
    def test_single_param(self):
        assert _extract_path_params("/partners/{id}") == ["id"]

    def test_multiple_params(self):
        assert _extract_path_params("/orders/{order_id}/lines/{line_id}") == [
            "order_id",
            "line_id",
        ]

    def test_no_params(self):
        assert _extract_path_params("/partners") == []


class TestTypeMapping:
    def test_int(self):
        assert _python_type_to_openapi(int) == "integer"

    def test_str(self):
        assert _python_type_to_openapi(str) == "string"

    def test_float(self):
        assert _python_type_to_openapi(float) == "number"

    def test_bool(self):
        assert _python_type_to_openapi(bool) == "boolean"

    def test_unknown(self):
        import inspect

        assert _python_type_to_openapi(inspect.Parameter.empty) == "string"


class TestGenerateOpenAPISpec:
    def test_basic_spec(self):
        api = _make_api()

        @api.get("/partners")
        def list_partners(env, **params):
            """List all partners."""

        spec = generate_openapi_spec(api)
        assert spec["openapi"] == "3.0.0"
        assert spec["info"]["title"] == "Test API"
        assert spec["info"]["version"] == "0.1.0"
        assert "/api/v1/partners" in spec["paths"]
        assert "get" in spec["paths"]["/api/v1/partners"]

    def test_path_params(self):
        api = _make_api()

        @api.get("/partners/{id}")
        def get_partner(env, id: int):
            """Get partner by ID."""

        spec = generate_openapi_spec(api)
        op = spec["paths"]["/api/v1/partners/{id}"]["get"]
        path_params = [p for p in op["parameters"] if p["in"] == "path"]
        assert len(path_params) == 1
        assert path_params[0]["name"] == "id"
        assert path_params[0]["required"] is True
        assert path_params[0]["schema"]["type"] == "integer"

    def test_query_params(self):
        api = _make_api()

        @api.get("/partners")
        def list_partners(env, limit: int = 80, search: str = ""):
            pass

        spec = generate_openapi_spec(api)
        op = spec["paths"]["/api/v1/partners"]["get"]
        query_params = [p for p in op["parameters"] if p["in"] == "query"]
        names = {p["name"] for p in query_params}
        assert "limit" in names
        assert "search" in names
        # Check default values
        limit_param = next(p for p in query_params if p["name"] == "limit")
        assert limit_param["schema"]["default"] == 80
        assert limit_param["required"] is False

    def test_post_has_request_body(self):
        api = _make_api()

        @api.post("/partners")
        def create_partner(env, body):
            pass

        spec = generate_openapi_spec(api)
        op = spec["paths"]["/api/v1/partners"]["post"]
        assert "requestBody" in op
        assert op["requestBody"]["required"] is True

    def test_get_no_request_body(self):
        api = _make_api()

        @api.get("/partners")
        def list_partners(env):
            pass

        spec = generate_openapi_spec(api)
        op = spec["paths"]["/api/v1/partners"]["get"]
        assert "requestBody" not in op

    def test_docstring_summary(self):
        api = _make_api()

        @api.get("/partners")
        def list_partners(env):
            """List all partners in the system."""

        spec = generate_openapi_spec(api)
        op = spec["paths"]["/api/v1/partners"]["get"]
        assert op["summary"] == "List all partners in the system."

    def test_no_docstring_uses_function_name(self):
        api = _make_api()

        @api.get("/partners")
        def list_partners(env):
            pass

        spec = generate_openapi_spec(api)
        op = spec["paths"]["/api/v1/partners"]["get"]
        assert op["summary"] == "List Partners"

    def test_custom_tags(self):
        api = _make_api()

        @api.get("/partners", tags=["Partners", "CRM"])
        def list_partners(env):
            pass

        spec = generate_openapi_spec(api)
        op = spec["paths"]["/api/v1/partners"]["get"]
        assert op["tags"] == ["Partners", "CRM"]

    def test_auth_adds_security_scheme(self):
        api = _make_api(auth="api_key")

        @api.get("/partners")
        def list_partners(env):
            pass

        spec = generate_openapi_spec(api)
        assert "securitySchemes" in spec["components"]
        assert "ApiKeyAuth" in spec["components"]["securitySchemes"]
        assert spec["security"] == [{"ApiKeyAuth": []}]

    def test_no_auth_no_security_scheme(self):
        api = _make_api(auth="none")

        @api.get("/partners")
        def list_partners(env):
            pass

        spec = generate_openapi_spec(api)
        assert "securitySchemes" not in spec.get("components", {})

    def test_multiple_methods_same_path(self):
        api = _make_api()

        @api.get("/partners")
        def list_partners(env):
            pass

        @api.post("/partners")
        def create_partner(env, body):
            pass

        spec = generate_openapi_spec(api)
        path_item = spec["paths"]["/api/v1/partners"]
        assert "get" in path_item
        assert "post" in path_item

    def test_description_in_info(self):
        api = _make_api(description="My cool API")
        spec = generate_openapi_spec(api)
        assert spec["info"]["description"] == "My cool API"

    def test_no_description_omitted(self):
        api = _make_api(description="")
        spec = generate_openapi_spec(api)
        assert "description" not in spec["info"]

    def test_kwargs_not_in_params(self):
        api = _make_api()

        @api.get("/partners")
        def list_partners(env, **params):
            pass

        spec = generate_openapi_spec(api)
        op = spec["paths"]["/api/v1/partners"]["get"]
        param_names = [p["name"] for p in op["parameters"]]
        assert "params" not in param_names


class TestSwaggerUIHtml:
    def test_contains_swagger_ui(self):
        html = get_swagger_ui_html("/api/v1/openapi.json", "My API")
        assert "swagger-ui" in html
        assert "/api/v1/openapi.json" in html
        assert "<title>My API</title>" in html

    def test_loads_from_cdn(self):
        html = get_swagger_ui_html("/openapi.json")
        assert "unpkg.com/swagger-ui-dist" in html
