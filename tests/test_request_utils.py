import json

import pytest

from odoo_rest_api.exceptions import BadRequest
from odoo_rest_api.request_utils import build_handler_args, parse_request


# ── Mock request objects ────────────────────────────────────────

class MockHttpRequest:
    """Mimics werkzeug request."""

    def __init__(self, method="GET", args=None, data=b"", content_type="", form=None):
        self.method = method
        self.args = args or {}
        self.data = data
        self.content_type = content_type
        self.form = form or {}


class MockOdooRequest:
    """Mimics odoo.http.request."""

    def __init__(self, httprequest):
        self.httprequest = httprequest


# ── parse_request tests ─────────────────────────────────────────

class TestParseRequest:
    def test_get_with_query_params(self):
        http_req = MockHttpRequest(method="GET", args={"limit": "10", "offset": "5"})
        request = MockOdooRequest(http_req)
        parsed = parse_request(request, {"id": "42"})

        assert parsed["path_params"] == {"id": "42"}
        assert parsed["query_params"] == {"limit": "10", "offset": "5"}
        assert parsed["body"] is None

    def test_post_json_body(self):
        body = {"name": "Alice", "email": "alice@example.com"}
        http_req = MockHttpRequest(
            method="POST",
            content_type="application/json",
            data=json.dumps(body).encode(),
        )
        request = MockOdooRequest(http_req)
        parsed = parse_request(request, {})

        assert parsed["body"] == body

    def test_post_invalid_json(self):
        http_req = MockHttpRequest(
            method="POST",
            content_type="application/json",
            data=b"not json{{{",
        )
        request = MockOdooRequest(http_req)
        with pytest.raises(BadRequest, match="Invalid JSON body"):
            parse_request(request, {})

    def test_post_form_data(self):
        http_req = MockHttpRequest(
            method="POST",
            content_type="application/x-www-form-urlencoded",
            form={"name": "Alice"},
        )
        request = MockOdooRequest(http_req)
        parsed = parse_request(request, {})

        assert parsed["body"] == {"name": "Alice"}

    def test_put_json_body(self):
        body = {"email": "updated@example.com"}
        http_req = MockHttpRequest(
            method="PUT",
            content_type="application/json",
            data=json.dumps(body).encode(),
        )
        request = MockOdooRequest(http_req)
        parsed = parse_request(request, {})

        assert parsed["body"] == body

    def test_patch_json_body(self):
        body = {"phone": "+123"}
        http_req = MockHttpRequest(
            method="PATCH",
            content_type="application/json",
            data=json.dumps(body).encode(),
        )
        request = MockOdooRequest(http_req)
        parsed = parse_request(request, {})

        assert parsed["body"] == body

    def test_get_no_body_parsed(self):
        http_req = MockHttpRequest(method="GET")
        request = MockOdooRequest(http_req)
        parsed = parse_request(request, {})

        assert parsed["body"] is None

    def test_delete_no_body_parsed(self):
        http_req = MockHttpRequest(method="DELETE")
        request = MockOdooRequest(http_req)
        parsed = parse_request(request, {})

        assert parsed["body"] is None


# ── build_handler_args tests ────────────────────────────────────

class TestBuildHandlerArgs:
    def test_env_injection(self):
        def handler(env):
            pass

        parsed = {"path_params": {}, "query_params": {}, "body": None}
        args = build_handler_args(handler, "mock_env", parsed)
        assert args == {"env": "mock_env"}

    def test_body_injection(self):
        def handler(env, body):
            pass

        parsed = {"path_params": {}, "query_params": {}, "body": {"name": "Alice"}}
        args = build_handler_args(handler, "mock_env", parsed)
        assert args == {"env": "mock_env", "body": {"name": "Alice"}}

    def test_path_param_injection(self):
        def handler(env, id):
            pass

        parsed = {"path_params": {"id": "42"}, "query_params": {}, "body": None}
        args = build_handler_args(handler, "mock_env", parsed)
        assert args == {"env": "mock_env", "id": "42"}

    def test_query_param_injection(self):
        def handler(env, search):
            pass

        parsed = {"path_params": {}, "query_params": {"search": "john"}, "body": None}
        args = build_handler_args(handler, "mock_env", parsed)
        assert args == {"env": "mock_env", "search": "john"}

    def test_kwargs_receives_remaining_query_params(self):
        def handler(env, **params):
            pass

        parsed = {
            "path_params": {},
            "query_params": {"limit": "10", "offset": "0"},
            "body": None,
        }
        args = build_handler_args(handler, "mock_env", parsed)
        assert args == {"env": "mock_env", "limit": "10", "offset": "0"}

    def test_named_param_consumed_from_query(self):
        """Named params should be consumed and not passed to **kwargs."""

        def handler(env, limit, **params):
            pass

        parsed = {
            "path_params": {},
            "query_params": {"limit": "10", "offset": "0"},
            "body": None,
        }
        args = build_handler_args(handler, "mock_env", parsed)
        assert args == {"env": "mock_env", "limit": "10", "offset": "0"}

    def test_full_signature(self):
        def handler(env, id, body, **params):
            pass

        parsed = {
            "path_params": {"id": "42"},
            "query_params": {"fields": "name,email"},
            "body": {"name": "Alice"},
        }
        args = build_handler_args(handler, "mock_env", parsed)
        assert args == {
            "env": "mock_env",
            "id": "42",
            "body": {"name": "Alice"},
            "fields": "name,email",
        }

    def test_missing_optional_params_not_included(self):
        def handler(env, id, body):
            pass

        parsed = {"path_params": {}, "query_params": {}, "body": None}
        args = build_handler_args(handler, "mock_env", parsed)
        # id not in path_params and body is None, but they're still set
        assert args == {"env": "mock_env", "body": None}
