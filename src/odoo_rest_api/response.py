import json
from datetime import date, datetime


def _is_recordset(obj):
    """Check if obj is an Odoo recordset (without importing odoo.models)."""
    return hasattr(obj, "_name") and hasattr(obj, "ids") and hasattr(obj, "read")


def serialize_data(data):
    """
    Recursively convert Odoo recordsets to dicts/lists before JSON encoding.

    - Multi-record recordset -> list of dicts via read()
    - Single record recordset -> dict via read()
    - Many2one field (recordset with 0-1 records) -> {"id": ..., "name": ...} or False
    - Lists/dicts -> recurse into values
    """
    if _is_recordset(data):
        records = data.read()
        # Recurse into each record dict to handle nested recordsets
        return [_serialize_dict(r) for r in records]

    if isinstance(data, dict):
        return _serialize_dict(data)

    if isinstance(data, list):
        return [serialize_data(item) for item in data]

    return data


def _serialize_dict(d):
    """Serialize dict values that may contain recordsets."""
    result = {}
    for key, value in d.items():
        if _is_recordset(value):
            # Nested recordset (e.g. Many2many field read manually)
            result[key] = value.read()
        else:
            result[key] = value
    return result


def json_serializer(obj):
    """Handle date, datetime, bytes, and any remaining Odoo types in JSON serialization."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, date):
        return obj.isoformat()
    if isinstance(obj, bytes):
        try:
            return obj.decode("utf-8")
        except UnicodeDecodeError:
            import base64
            return base64.b64encode(obj).decode("ascii")
    if _is_recordset(obj):
        return obj.read()
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


def success_response(data, count=None, status=200):
    """Build a standardized JSON success response."""
    from werkzeug.wrappers import Response

    body = {
        "success": True,
        "data": serialize_data(data),
        "error": None,
    }
    if count is not None:
        body["count"] = count
    return Response(
        json.dumps(body, default=json_serializer),
        status=status,
        content_type="application/json",
    )


def error_response(message, status=500, error_type="ServerError", details=None, simple_error=False):
    """Build a standardized JSON error response."""
    from werkzeug.wrappers import Response

    if simple_error:
        error_value = message
    else:
        error_value = {
            "type": error_type,
            "message": message,
        }
        if details is not None:
            error_value["details"] = details

    body = {
        "success": False,
        "data": None,
        "error": error_value,
    }
    return Response(
        json.dumps(body, default=json_serializer),
        status=status,
        content_type="application/json",
    )
