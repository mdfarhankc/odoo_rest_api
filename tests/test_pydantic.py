"""Tests for pydantic input/output validation and OpenAPI schema generation."""

import pytest

try:
    from pydantic import BaseModel
    HAS_PYDANTIC = True
except ImportError:
    HAS_PYDANTIC = False

from odoo_rest_api.api import OdooRestAPI, RouteDefinition
from odoo_rest_api.docs import generate_openapi_spec, _get_pydantic_schema

pytestmark = pytest.mark.skipif(not HAS_PYDANTIC, reason="pydantic not installed")


# ── Test models ──────────────────────────────────────────────────

class PartnerCreate(BaseModel):
    name: str
    email: str = None
    phone: str = None


class PartnerOut(BaseModel):
    id: int
    name: str
    email: str = None


class AddressModel(BaseModel):
    street: str
    city: str
    zip: str = None


class PartnerWithAddress(BaseModel):
    name: str
    address: AddressModel


# ── Schema extraction tests ──────────────────────────────────────


class TestGetPydanticSchema:
    def test_extracts_schema(self):
        schema = _get_pydantic_schema(PartnerCreate)
        assert schema is not None
        assert "properties" in schema
        assert "name" in schema["properties"]
        assert "email" in schema["properties"]

    def test_required_fields(self):
        schema = _get_pydantic_schema(PartnerCreate)
        assert "name" in schema.get("required", [])

    def test_optional_fields_not_required(self):
        schema = _get_pydantic_schema(PartnerCreate)
        required = schema.get("required", [])
        assert "email" not in required
        assert "phone" not in required

    def test_none_model_returns_none(self):
        assert _get_pydantic_schema(None) is None

    def test_nested_model_has_defs(self):
        schema = _get_pydantic_schema(PartnerWithAddress)
        # Pydantic v2 puts nested models in $defs
        assert "$defs" in schema or "definitions" in schema


# ── Route definition tests ───────────────────────────────────────


class TestRouteDefinitionModels:
    def test_input_model_stored(self):
        api = OdooRestAPI(prefix="/api/v1")

        @api.post("/partners", input_model=PartnerCreate)
        def create_partner(env, body):
            pass

        assert api.routes[0].input_model is PartnerCreate

    def test_output_model_stored(self):
        api = OdooRestAPI(prefix="/api/v1")

        @api.get("/partners/{id}", output_model=PartnerOut)
        def get_partner(env, id):
            pass

        assert api.routes[0].output_model is PartnerOut

    def test_both_models_stored(self):
        api = OdooRestAPI(prefix="/api/v1")

        @api.post("/partners", input_model=PartnerCreate, output_model=PartnerOut)
        def create_partner(env, body):
            pass

        assert api.routes[0].input_model is PartnerCreate
        assert api.routes[0].output_model is PartnerOut

    def test_no_models_default_none(self):
        api = OdooRestAPI(prefix="/api/v1")

        @api.get("/partners")
        def list_partners(env):
            pass

        assert api.routes[0].input_model is None
        assert api.routes[0].output_model is None


# ── OpenAPI spec generation with pydantic ────────────────────────


class TestOpenAPISpecWithPydantic:
    def test_input_model_in_request_body(self):
        api = OdooRestAPI(prefix="/api/v1", title="Test", version="0.1")

        @api.post("/partners", input_model=PartnerCreate)
        def create_partner(env, body):
            pass

        spec = generate_openapi_spec(api)
        op = spec["paths"]["/api/v1/partners"]["post"]
        body_schema = op["requestBody"]["content"]["application/json"]["schema"]
        assert "properties" in body_schema
        assert "name" in body_schema["properties"]

    def test_input_model_adds_422_response(self):
        api = OdooRestAPI(prefix="/api/v1", title="Test", version="0.1")

        @api.post("/partners", input_model=PartnerCreate)
        def create_partner(env, body):
            pass

        spec = generate_openapi_spec(api)
        op = spec["paths"]["/api/v1/partners"]["post"]
        assert "422" in op["responses"]

    def test_no_input_model_no_422(self):
        api = OdooRestAPI(prefix="/api/v1", title="Test", version="0.1")

        @api.post("/partners")
        def create_partner(env, body):
            pass

        spec = generate_openapi_spec(api)
        op = spec["paths"]["/api/v1/partners"]["post"]
        assert "422" not in op["responses"]

    def test_output_model_in_success_response(self):
        api = OdooRestAPI(prefix="/api/v1", title="Test", version="0.1")

        @api.get("/partners/{id}", output_model=PartnerOut)
        def get_partner(env, id):
            pass

        spec = generate_openapi_spec(api)
        op = spec["paths"]["/api/v1/partners/{id}"]["get"]
        resp_schema = op["responses"]["200"]["content"]["application/json"]["schema"]
        # Should have the envelope with data containing the output model
        assert resp_schema["properties"]["data"]["properties"]["id"]["type"] == "integer"
        assert resp_schema["properties"]["data"]["properties"]["name"]["type"] == "string"

    def test_no_output_model_uses_generic_response(self):
        api = OdooRestAPI(prefix="/api/v1", title="Test", version="0.1")

        @api.get("/partners")
        def list_partners(env):
            pass

        spec = generate_openapi_spec(api)
        op = spec["paths"]["/api/v1/partners"]["get"]
        resp_schema = op["responses"]["200"]["content"]["application/json"]["schema"]
        assert "$ref" in resp_schema

    def test_nested_model_defs_in_components(self):
        api = OdooRestAPI(prefix="/api/v1", title="Test", version="0.1")

        @api.post("/partners", input_model=PartnerWithAddress)
        def create_partner(env, body):
            pass

        spec = generate_openapi_spec(api)
        # Nested AddressModel should be in components/schemas
        assert "AddressModel" in spec["components"]["schemas"]

    def test_both_models_in_spec(self):
        api = OdooRestAPI(prefix="/api/v1", title="Test", version="0.1")

        @api.post("/partners", input_model=PartnerCreate, output_model=PartnerOut)
        def create_partner(env, body):
            pass

        spec = generate_openapi_spec(api)
        op = spec["paths"]["/api/v1/partners"]["post"]

        # Input schema in request body
        body_schema = op["requestBody"]["content"]["application/json"]["schema"]
        assert "name" in body_schema["properties"]

        # Output schema in response
        resp_schema = op["responses"]["200"]["content"]["application/json"]["schema"]
        assert "id" in resp_schema["properties"]["data"]["properties"]


# ── Input validation tests ───────────────────────────────────────


class TestInputValidation:
    """Test the validate_input function directly."""

    def test_valid_input(self):
        from odoo_rest_api.validation import validate_input
        result = validate_input(PartnerCreate, {"name": "Alice", "email": "alice@test.com"})
        assert result["name"] == "Alice"
        assert result["email"] == "alice@test.com"

    def test_valid_input_optional_fields(self):
        from odoo_rest_api.validation import validate_input
        result = validate_input(PartnerCreate, {"name": "Alice"})
        assert result["name"] == "Alice"
        assert result["email"] is None

    def test_invalid_input_missing_required(self):
        from odoo_rest_api.validation import validate_input
        from odoo_rest_api.exceptions import ValidationError

        with pytest.raises(ValidationError) as exc_info:
            validate_input(PartnerCreate, {"email": "alice@test.com"})

        assert exc_info.value.status_code == 422
        assert exc_info.value.details is not None
        assert len(exc_info.value.details) > 0

    def test_invalid_input_wrong_type(self):
        from odoo_rest_api.validation import validate_input
        from odoo_rest_api.exceptions import ValidationError

        with pytest.raises(ValidationError):
            validate_input(PartnerOut, {"id": "not_an_int", "name": "Alice"})

    def test_validation_error_has_field_details(self):
        from odoo_rest_api.validation import validate_input
        from odoo_rest_api.exceptions import ValidationError

        with pytest.raises(ValidationError) as exc_info:
            validate_input(PartnerCreate, {})

        details = exc_info.value.details
        assert any("name" in d.get("field", "") for d in details)


# ── Output validation tests ──────────────────────────────────────


class TestOutputValidation:
    """Test the validate_output function directly."""

    def test_valid_output_dict(self):
        from odoo_rest_api.validation import validate_output
        result = validate_output(PartnerOut, {"id": 1, "name": "Alice", "email": "a@b.com"})
        assert result == {"id": 1, "name": "Alice", "email": "a@b.com"}

    def test_output_strips_extra_fields(self):
        from odoo_rest_api.validation import validate_output
        result = validate_output(PartnerOut, {
            "id": 1, "name": "Alice", "email": "a@b.com",
            "phone": "123", "street": "Main St"
        })
        assert "phone" not in result
        assert "street" not in result

    def test_output_list(self):
        from odoo_rest_api.validation import validate_output
        data = [
            {"id": 1, "name": "Alice"},
            {"id": 2, "name": "Bob"},
        ]
        result = validate_output(PartnerOut, data)
        assert len(result) == 2
        assert result[0]["id"] == 1
        assert result[1]["name"] == "Bob"

    def test_invalid_output_returns_raw_data(self):
        from odoo_rest_api.validation import validate_output
        # Missing required field, output validation should not crash
        data = {"email": "a@b.com"}
        result = validate_output(PartnerOut, data)
        # Should return raw data since validation failed
        assert result == data
