"""
Pydantic-based input/output validation for route handlers.

Pydantic is optional, and these functions are only called when
``input_model`` or ``output_model`` is set on a route.
"""

import logging

from .exceptions import ValidationError

_logger = logging.getLogger(__name__)


def validate_input(model, body):
    """Validate request body against a pydantic model.

    Returns the validated data as a dict.
    Raises ValidationError with field-level details on failure.
    """
    try:
        if hasattr(model, "model_validate"):
            # Pydantic v2
            instance = model.model_validate(body)
            return instance.model_dump()
        else:
            # Pydantic v1
            instance = model(**body)
            return instance.dict()
    except Exception as exc:
        errors = _extract_pydantic_errors(exc)
        raise ValidationError(
            message="Request validation failed",
            details=errors,
        )


def validate_output(model, data):
    """Validate/serialize response data through a pydantic model.

    Accepts a dict or a list of dicts. Returns serialized data.
    """
    try:
        if isinstance(data, list):
            return [_serialize_one(model, item) for item in data]
        return _serialize_one(model, data)
    except Exception:
        # If output validation fails, log but don't crash, and return raw data
        _logger.warning("Output validation failed for model %s", model.__name__, exc_info=True)
        return data


def _serialize_one(model, item):
    """Validate and serialize a single item through a pydantic model."""
    if not isinstance(item, dict):
        # Try to convert recordset-like objects
        if hasattr(item, "read"):
            item = item.read()[0]
        else:
            item = dict(item)

    if hasattr(model, "model_validate"):
        # Pydantic v2
        return model.model_validate(item).model_dump()
    else:
        # Pydantic v1
        return model(**item).dict()


def _extract_pydantic_errors(exc):
    """Extract structured errors from a pydantic ValidationError."""
    if hasattr(exc, "errors"):
        errors = exc.errors() if callable(exc.errors) else exc.errors
        return [
            {
                "field": " → ".join(str(loc) for loc in err.get("loc", [])),
                "message": err.get("msg", str(err)),
                "type": err.get("type", ""),
            }
            for err in errors
        ]
    return [{"message": str(exc)}]
