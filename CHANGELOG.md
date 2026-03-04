# Changelog

All notable changes to this project will be documented in this file.

## [0.2.1] - 2026-03-04

### Fixed
- Swagger UI "No layout defined for StandaloneLayout" error — added missing `swagger-ui-standalone-preset.js` script

## [0.2.0] - 2026-03-04

### Added
- **Auto-generated API documentation** — `GET {prefix}/docs` serves Swagger UI, `GET {prefix}/openapi.json` serves the OpenAPI 3.0 spec
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
