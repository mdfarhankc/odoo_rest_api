import json
import sys
import types
from datetime import date, datetime
from unittest.mock import MagicMock

# ── Mock werkzeug so response.py can be imported without it ──
_mock_werkzeug = types.ModuleType("werkzeug")
_mock_wrappers = types.ModuleType("werkzeug.wrappers")


class _FakeResponse:
    """Minimal stand-in for werkzeug.wrappers.Response."""

    def __init__(self, response=None, status=None, content_type=None):
        self.data = response.encode() if isinstance(response, str) else response
        self.status_code = status
        self.content_type = content_type


_mock_wrappers.Response = _FakeResponse
_mock_werkzeug.wrappers = _mock_wrappers
sys.modules.setdefault("werkzeug", _mock_werkzeug)
sys.modules.setdefault("werkzeug.wrappers", _mock_wrappers)

from odoo_rest_api.response import (
    json_serializer,
    serialize_data,
    success_response,
    error_response,
    _is_recordset,
)


# ── Mock recordset for testing ──────────────────────────────────

class MockRecordset:
    """Mimics an Odoo recordset for serialization tests."""

    def __init__(self, records, model_name="res.partner"):
        self._records = records
        self._name = model_name
        self.ids = [r["id"] for r in records]

    def read(self, fields=None):
        if fields:
            return [{k: r[k] for k in fields if k in r} for r in self._records]
        return list(self._records)


class TestIsRecordset:
    def test_mock_recordset(self):
        rs = MockRecordset([{"id": 1, "name": "Alice"}])
        assert _is_recordset(rs) is True

    def test_plain_dict(self):
        assert _is_recordset({"id": 1}) is False

    def test_plain_list(self):
        assert _is_recordset([1, 2, 3]) is False

    def test_string(self):
        assert _is_recordset("hello") is False


class TestJsonSerializer:
    def test_datetime(self):
        dt = datetime(2026, 3, 4, 12, 30, 0)
        assert json_serializer(dt) == "2026-03-04T12:30:00"

    def test_date(self):
        d = date(2026, 3, 4)
        assert json_serializer(d) == "2026-03-04"

    def test_bytes_utf8(self):
        assert json_serializer(b"hello") == "hello"

    def test_bytes_binary(self):
        # Non-UTF8 bytes should be base64 encoded
        result = json_serializer(b"\x80\x81\x82")
        import base64
        assert result == base64.b64encode(b"\x80\x81\x82").decode("ascii")

    def test_unsupported_type_raises(self):
        import pytest
        with pytest.raises(TypeError, match="set"):
            json_serializer({1, 2, 3})


class TestSerializeData:
    def test_recordset(self):
        rs = MockRecordset([
            {"id": 1, "name": "Alice"},
            {"id": 2, "name": "Bob"},
        ])
        result = serialize_data(rs)
        assert result == [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]

    def test_dict_passthrough(self):
        data = {"id": 1, "name": "Alice"}
        result = serialize_data(data)
        assert result == {"id": 1, "name": "Alice"}

    def test_list_of_dicts(self):
        data = [{"id": 1}, {"id": 2}]
        result = serialize_data(data)
        assert result == [{"id": 1}, {"id": 2}]

    def test_nested_recordset_in_dict(self):
        inner_rs = MockRecordset([{"id": 10, "name": "Tag1"}], "res.tag")
        data = {"id": 1, "name": "Alice", "tags": inner_rs}
        result = serialize_data(data)
        assert result["tags"] == [{"id": 10, "name": "Tag1"}]

    def test_plain_string(self):
        assert serialize_data("hello") == "hello"

    def test_plain_int(self):
        assert serialize_data(42) == 42

    def test_none(self):
        assert serialize_data(None) is None

    def test_empty_recordset(self):
        rs = MockRecordset([])
        result = serialize_data(rs)
        assert result == []


class TestSuccessResponse:
    def test_basic(self):
        resp = success_response({"id": 1, "name": "Alice"})
        assert resp.status_code == 200
        assert resp.content_type == "application/json"
        body = json.loads(resp.data)
        assert body["success"] is True
        assert body["data"] == {"id": 1, "name": "Alice"}
        assert body["error"] is None

    def test_with_count(self):
        resp = success_response([1, 2, 3], count=100)
        body = json.loads(resp.data)
        assert body["count"] == 100

    def test_custom_status(self):
        resp = success_response({"id": 1}, status=201)
        assert resp.status_code == 201

    def test_recordset_auto_serialized(self):
        rs = MockRecordset([{"id": 1, "name": "Alice"}])
        resp = success_response(rs)
        body = json.loads(resp.data)
        assert body["data"] == [{"id": 1, "name": "Alice"}]


class TestErrorResponse:
    def test_basic(self):
        resp = error_response("Something went wrong")
        assert resp.status_code == 500
        body = json.loads(resp.data)
        assert body["success"] is False
        assert body["data"] is None
        assert body["error"]["type"] == "ServerError"
        assert body["error"]["message"] == "Something went wrong"

    def test_custom_status_and_type(self):
        resp = error_response("Not found", status=404, error_type="NotFound")
        assert resp.status_code == 404
        body = json.loads(resp.data)
        assert body["error"]["type"] == "NotFound"

    def test_with_details(self):
        resp = error_response("Bad", status=400, details={"field": "email"})
        body = json.loads(resp.data)
        assert body["error"]["details"] == {"field": "email"}

    def test_without_details(self):
        resp = error_response("Bad", status=400)
        body = json.loads(resp.data)
        assert "details" not in body["error"]
