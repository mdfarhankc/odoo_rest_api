# Changelog

All notable changes to this project will be documented in this file.

## [0.3.0] - 2026-03-14

### Added
- **Pydantic input/output validation**: `input_model` and `output_model` on route decorators for automatic request validation (422 on failure) and response serialization. Supports both Pydantic v1 and v2
- **Pydantic schemas in OpenAPI spec**: Input models appear in request body schema, output models in response schema, nested model `$defs` merged into `components/schemas`, 422 response auto-added for validated routes
- **Route overriding**: Decorating the same method+path replaces the previous handler (last wins)
- **Priority-based route overriding**: `@api.get('/partners', priority=10)` lets higher-priority routes win, useful for controlled inheritance across Odoo addons
- **Simple error format**: `simple_error=True` on `OdooRestAPI` returns error as a plain string instead of `{"type": ..., "message": ...}` object
- New `odoo_rest_api/validation.py` module (no Odoo imports, fully testable standalone)

### Changed
- Validation logic separated from `routing.py` into `validation.py` for testability without Odoo
- Error response `error` field is now configurable (object or string) via `simple_error` parameter

## [0.2.2] - 2026-03-04

### Changed
* Updated PyPI metadata (keywords, classifiers, project URLs)
* Improved package discoverability on PyPI

## [0.2.1] - 2026-03-04

### Fixed
- Swagger UI "No layout defined for StandaloneLayout" error, caused by the missing `swagger-ui-standalone-preset.js` script

## [0.2.0] - 2026-03-04

### Added
- **Auto-generated API documentation**: `GET {prefix}/docs` serves Swagger UI, `GET {prefix}/openapi.json` serves the OpenAPI 3.0 spec
- OpenAPI spec auto-generated from registered routes, handler signatures, docstrings, and type hints
- `docs`, `title`, `version`, `description` parameters on `OdooRestAPI`
- `tags` parameter on route decorators for custom endpoint grouping
- `generate_openapi_spec()` exported for advanced use cases
- Analytics example with raw SQL queries, dashboard stats, and aggregations

### Changed
- Renamed `OdooAPI` to `OdooRestAPI`

## [0.1.0] - 2026-03-03

### Added
- Initial release
- Decorator-based routing (`@api.get()`, `@api.post()`, `@api.put()`, `@api.patch()`, `@api.delete()`)
- Dynamic `http.Controller` generation via `api.register()`
- Standardized JSON responses (`{success, data, error}`)
- Automatic recordset serialization (return `search()` directly)
- Automatic request parsing (JSON body, query params, path params via signature inspection)
- Exception classes mapping to HTTP status codes (400–429)
- Pluggable authentication via `auth_handler` or `register_auth_handler()`
- Multi-file API support (shared instance pattern)
- Catch-all 404 route for unmatched API paths
- `PaginationParams` helper
- Odoo 16+ compatible
