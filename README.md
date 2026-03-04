# odoo-rest-api

A decorator-based REST API framework for Odoo. Create clean, standardized REST endpoints inside your Odoo modules with a FastAPI-like developer experience.

## Features

- **Decorator-based routing** — `@api.get()`, `@api.post()`, `@api.put()`, `@api.patch()`, `@api.delete()`
- **API key authentication** — Custom `rest.api.key` model with per-user keys, scopes, rate limiting, and expiration
- **Standardized JSON responses** — Consistent `{success, data, error}` format
- **Automatic request parsing** — JSON body, query params, and path params injected into handler functions via signature inspection
- **Error handling** — Exception classes map to proper HTTP status codes
- **Odoo ORM access** — Handlers receive an authenticated `env` bound to the API key's user
- **Odoo 16+ compatible**

## Installation

This project has two parts:

### 1. Install the pip package

```bash
pip install odoo-rest-api
```

### 2. Install the Odoo addon

Copy the `odoo_rest_api_base/` directory into your Odoo addons path, then install **Odoo REST API Base** from the Apps menu.

### 3. Add dependency in your module

In your custom module's `__manifest__.py`:

```python
{
    "depends": ["odoo_rest_api_base"],
}
```

## Quick Start

In your addon's controller file:

```python
# my_addon/controllers/partner_api.py
from odoo_rest_api import OdooAPI, NotFound

api = OdooAPI(prefix='/api/v1')

@api.get('/partners')
def list_partners(env, **params):
    partners = env['res.partner'].search_read([], ['name', 'email'])
    return partners

@api.get('/partners/{id}')
def get_partner(env, id):
    partner = env['res.partner'].browse(int(id))
    if not partner.exists():
        raise NotFound('Partner not found')
    return partner.read(['name', 'email'])[0]

@api.post('/partners')
def create_partner(env, body):
    partner = env['res.partner'].create(body)
    return partner.read(['name', 'email'])[0]

@api.put('/partners/{id}')
def update_partner(env, id, body):
    partner = env['res.partner'].browse(int(id))
    if not partner.exists():
        raise NotFound('Partner not found')
    partner.write(body)
    return partner.read(['name', 'email'])[0]

@api.delete('/partners/{id}')
def delete_partner(env, id):
    partner = env['res.partner'].browse(int(id))
    if not partner.exists():
        raise NotFound('Partner not found')
    partner.unlink()
    return {'deleted': True}

# IMPORTANT: Must be called at module level
api.register()
```

Don't forget to import the controller in your module's `controllers/__init__.py`:

```python
from . import partner_api
```

## Authentication

1. Go to **Settings > REST API > API Keys** in the Odoo backend
2. Create a new API key and link it to an Odoo user
3. Pass the key in the `X-API-Key` header:

```bash
curl -H "X-API-Key: your-api-key-here" \
     http://localhost:8069/api/v1/partners
```

## Response Format

### Success

```json
{
    "success": true,
    "data": [{"id": 1, "name": "Alice", "email": "alice@example.com"}],
    "error": null
}
```

### Error

```json
{
    "success": false,
    "data": null,
    "error": {
        "type": "NotFound",
        "message": "Partner not found"
    }
}
```

## Exceptions

| Exception | Status Code |
|---|---|
| `BadRequest` | 400 |
| `Unauthorized` | 401 |
| `Forbidden` | 403 |
| `NotFound` | 404 |
| `MethodNotAllowed` | 405 |
| `Conflict` | 409 |
| `ValidationError` | 422 |
| `RateLimitExceeded` | 429 |

## Alternative: Auth Method for Hand-Written Controllers

If you prefer Odoo's native controller style, use `auth='rest_api_key'`:

```python
from odoo import http

class MyController(http.Controller):
    @http.route('/my/endpoint', type='http', auth='rest_api_key', csrf=False)
    def my_handler(self, **kwargs):
        partners = http.request.env['res.partner'].search_read([], ['name'])
        return http.request.make_json_response(partners)
```

## License

LGPL-3.0
