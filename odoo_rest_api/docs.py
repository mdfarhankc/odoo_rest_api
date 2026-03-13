"""
Auto-generated OpenAPI 3.0 spec and Swagger UI for OdooRestAPI instances.
"""

import inspect
import re

# Map Python type hints to OpenAPI types
_TYPE_MAP = {
    int: "integer",
    float: "number",
    str: "string",
    bool: "boolean",
    list: "array",
    dict: "object",
}


def _python_type_to_openapi(annotation):
    if annotation is inspect.Parameter.empty:
        return "string"
    return _TYPE_MAP.get(annotation, "string")


def _parse_docstring(func):
    """Extract summary (first line) and description (rest) from a docstring."""
    doc = inspect.getdoc(func)
    if not doc:
        return "", ""
    lines = doc.strip().splitlines()
    summary = lines[0].strip()
    description = "\n".join(lines[1:]).strip() if len(lines) > 1 else ""
    return summary, description


def _get_tag(route_def):
    """Derive a tag from the handler's module name (last segment)."""
    module = getattr(route_def.handler, "__module__", "") or ""
    tag = module.rsplit(".", 1)[-1] if module else "default"
    # Clean up common prefixes
    if tag == "__init__":
        parts = module.rsplit(".", 2)
        tag = parts[-2] if len(parts) >= 2 else "default"
    return tag


def _extract_path_params(path):
    """Extract parameter names from {param} syntax in path."""
    return re.findall(r"\{(\w+)\}", path)


def _get_pydantic_schema(model):
    """Extract JSON Schema from a pydantic model (supports v1 and v2)."""
    if model is None:
        return None
    try:
        if hasattr(model, "model_json_schema"):
            # Pydantic v2
            return model.model_json_schema()
        elif hasattr(model, "schema"):
            # Pydantic v1
            return model.schema()
    except Exception:
        pass
    return None


def _build_operation(route_def, api_instance):
    """Build an OpenAPI operation object for a single route."""
    handler = route_def.handler
    summary, description = _parse_docstring(handler)
    path_param_names = _extract_path_params(route_def.path)

    operation = {
        "operationId": handler.__name__,
        "summary": summary or handler.__name__.replace("_", " ").title(),
        "tags": route_def.tags if route_def.tags else [_get_tag(route_def)],
        "parameters": [],
        "responses": {
            "200": {
                "description": "Successful response",
                "content": {
                    "application/json": {
                        "schema": {"$ref": "#/components/schemas/SuccessResponse"}
                    }
                },
            },
            "500": {
                "description": "Internal server error",
                "content": {
                    "application/json": {
                        "schema": {"$ref": "#/components/schemas/ErrorResponse"}
                    }
                },
            },
        },
    }

    if description:
        operation["description"] = description

    # Add 401 response if route has auth
    if route_def.auth not in ("none", "public"):
        operation["responses"]["401"] = {
            "description": "Unauthorized",
            "content": {
                "application/json": {
                    "schema": {"$ref": "#/components/schemas/ErrorResponse"}
                }
            },
        }
        operation["security"] = [{"ApiKeyAuth": []}]
    elif api_instance.auth not in ("none", "public"):
        # API-level auth but route overrides to none, so no security on this route
        operation["security"] = []

    # Path parameters
    sig = inspect.signature(handler)
    for param_name in path_param_names:
        param_schema = {"type": "string"}
        if param_name in sig.parameters:
            annotation = sig.parameters[param_name].annotation
            param_schema["type"] = _python_type_to_openapi(annotation)

        operation["parameters"].append({
            "name": param_name,
            "in": "path",
            "required": True,
            "schema": param_schema,
        })

    # Query parameters (named params that aren't env, body, or path params)
    for name, param in sig.parameters.items():
        if name in ("env", "body", "self") or name in path_param_names:
            continue
        if param.kind == inspect.Parameter.VAR_KEYWORD:
            continue
        if param.kind == inspect.Parameter.VAR_POSITIONAL:
            continue

        param_schema = {"type": _python_type_to_openapi(param.annotation)}
        if param.default is not inspect.Parameter.empty:
            param_schema["default"] = param.default

        operation["parameters"].append({
            "name": name,
            "in": "query",
            "required": param.default is inspect.Parameter.empty,
            "schema": param_schema,
        })

    # Request body for POST/PUT/PATCH
    if route_def.method in ("POST", "PUT", "PATCH"):
        input_schema = _get_pydantic_schema(route_def.input_model)
        if input_schema:
            # Strip $defs from inline schema, they are merged at spec level
            body_schema = {k: v for k, v in input_schema.items() if k != "$defs"}
        else:
            body_schema = {"type": "object"}

        operation["requestBody"] = {
            "required": True,
            "content": {
                "application/json": {
                    "schema": body_schema,
                }
            },
        }

        # Add 422 response when input validation is configured
        if route_def.input_model:
            operation["responses"]["422"] = {
                "description": "Validation error",
                "content": {
                    "application/json": {
                        "schema": {"$ref": "#/components/schemas/ErrorResponse"}
                    }
                },
            }

    # Output schema in success response
    output_schema = _get_pydantic_schema(route_def.output_model)
    if output_schema:
        out_schema = {k: v for k, v in output_schema.items() if k != "$defs"}
        operation["responses"]["200"] = {
            "description": "Successful response",
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "success": {"type": "boolean", "example": True},
                            "data": out_schema,
                            "error": {"type": "null"},
                        },
                    }
                }
            },
        }

    return operation


def generate_openapi_spec(api_instance):
    """
    Build an OpenAPI 3.0.0 spec dict from an OdooRestAPI instance's routes.
    """
    spec = {
        "openapi": "3.0.0",
        "info": {
            "title": api_instance.title,
            "version": api_instance.version,
        },
        "paths": {},
        "components": {
            "schemas": {
                "SuccessResponse": {
                    "type": "object",
                    "properties": {
                        "success": {"type": "boolean", "example": True},
                        "data": {},
                        "error": {"type": "null"},
                    },
                },
                "ErrorResponse": {
                    "type": "object",
                    "properties": {
                        "success": {"type": "boolean", "example": False},
                        "data": {"type": "null"},
                        "error": {"type": "string"}
                        if getattr(api_instance, "simple_error", False)
                        else {
                            "type": "object",
                            "properties": {
                                "type": {"type": "string"},
                                "message": {"type": "string"},
                            },
                        },
                    },
                },
            },
        },
    }

    if api_instance.description:
        spec["info"]["description"] = api_instance.description

    # Security scheme if API-level auth is set
    if api_instance.auth not in ("none", "public"):
        spec["components"]["securitySchemes"] = {
            "ApiKeyAuth": {
                "type": "apiKey",
                "in": "header",
                "name": "X-API-Key",
            }
        }
        spec["security"] = [{"ApiKeyAuth": []}]

    # Build paths and collect $defs from pydantic models
    for route_def in api_instance.routes:
        path = route_def.path
        method = route_def.method.lower()
        operation = _build_operation(route_def, api_instance)

        if path not in spec["paths"]:
            spec["paths"][path] = {}
        spec["paths"][path][method] = operation

        # Merge $defs from pydantic schemas into components/schemas
        for model in (route_def.input_model, route_def.output_model):
            schema = _get_pydantic_schema(model)
            if schema and "$defs" in schema:
                for def_name, def_schema in schema["$defs"].items():
                    spec["components"]["schemas"][def_name] = def_schema

    return spec


def get_swagger_ui_html(openapi_url, title="API Documentation"):
    """Return an HTML page that loads Swagger UI from CDN."""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist@5/swagger-ui.css">
    <style>
        html {{ box-sizing: border-box; overflow-y: scroll; }}
        *, *:before, *:after {{ box-sizing: inherit; }}
        body {{ margin: 0; background: #fafafa; }}
    </style>
</head>
<body>
    <div id="swagger-ui"></div>
    <script src="https://unpkg.com/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
    <script src="https://unpkg.com/swagger-ui-dist@5/swagger-ui-standalone-preset.js"></script>
    <script>
        SwaggerUIBundle({{
            url: "{openapi_url}",
            dom_id: "#swagger-ui",
            presets: [
                SwaggerUIBundle.presets.apis,
                SwaggerUIStandalonePreset
            ],
            layout: "StandaloneLayout",
            deepLinking: true,
            defaultModelsExpandDepth: -1
        }});
    </script>
</body>
</html>"""
