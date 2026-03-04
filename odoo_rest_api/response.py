import json
from datetime import date, datetime


def json_serializer(obj):
    """Handle date, datetime, and Odoo recordsets in JSON serialization."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, date):
        return obj.isoformat()
    if hasattr(obj, "ids"):
        return obj.ids
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


def success_response(data, count=None, status=200):
    """Build a standardized JSON success response."""
    from werkzeug.wrappers import Response

    body = {
        "success": True,
        "data": data,
        "error": None,
    }
    if count is not None:
        body["count"] = count
    return Response(
        json.dumps(body, default=json_serializer),
        status=status,
        content_type="application/json",
    )


def error_response(message, status=500, error_type="ServerError", details=None):
    """Build a standardized JSON error response."""
    from werkzeug.wrappers import Response

    body = {
        "success": False,
        "data": None,
        "error": {
            "type": error_type,
            "message": message,
        },
    }
    if details is not None:
        body["error"]["details"] = details
    return Response(
        json.dumps(body, default=json_serializer),
        status=status,
        content_type="application/json",
    )
