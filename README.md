# odoo-rest-api

![PyPI](https://img.shields.io/pypi/v/odoo-rest-api)
![Python](https://img.shields.io/pypi/pyversions/odoo-rest-api)
![License](https://img.shields.io/pypi/l/odoo-rest-api)

A decorator-based REST API framework for Odoo. Create clean, standardized REST endpoints inside your Odoo modules with a FastAPI-like developer experience.

## Features

- **Decorator-based routing** — `@api.get()`, `@api.post()`, `@api.put()`, `@api.patch()`, `@api.delete()`
- **Standardized JSON responses** — Consistent `{success, data, error}` format
- **Automatic recordset serialization** — Return `env['res.partner'].search()` directly, recordsets are auto-converted to dicts
- **Automatic request parsing** — JSON body, query params, and path params injected via signature inspection
- **Error handling** — Exception classes map to proper HTTP status codes
- **Pluggable authentication** — Bring your own auth logic
- **Multi-file support** — Share one API instance across partner.py, order.py, etc.
- **Odoo 16+ compatible**

## Installation

```bash
pip install odoo-rest-api
```

No Odoo module dependency needed — just a pip package.

## Quick Start

### Single file

```python
# my_addon/controllers/partner_api.py
from odoo_rest_api import OdooRestAPI, NotFound, BadRequest

api = OdooRestAPI(prefix='/api/v1')

@api.get('/partners')
def list_partners(env, **params):
    limit = min(int(params.get('limit', 80)), 1000)
    offset = int(params.get('offset', 0))
    return env['res.partner'].search_read(
        [], ['name', 'email', 'phone'], limit=limit, offset=offset
    )

@api.get('/partners/{id}')
def get_partner(env, id):
    partner = env['res.partner'].browse(int(id))
    if not partner.exists():
        raise NotFound('Partner not found')
    return partner.read(['name', 'email', 'phone'])[0]

@api.post('/partners')
def create_partner(env, body):
    if not body or not body.get('name'):
        raise BadRequest("'name' is required")
    partner = env['res.partner'].create(body)
    return partner.read(['name', 'email', 'phone'])[0]

@api.put('/partners/{id}')
def update_partner(env, id, body):
    partner = env['res.partner'].browse(int(id))
    if not partner.exists():
        raise NotFound('Partner not found')
    partner.write(body)
    return partner.read(['name', 'email', 'phone'])[0]

@api.delete('/partners/{id}')
def delete_partner(env, id):
    partner = env['res.partner'].browse(int(id))
    if not partner.exists():
        raise NotFound('Partner not found')
    partner.unlink()
    return {'deleted': True}

api.register()
```

```python
# my_addon/controllers/__init__.py
from . import partner_api
```

### Multi-file (recommended)

Share one API instance across multiple files:

```python
# controllers/app.py — shared instance
from odoo_rest_api import OdooRestAPI
api = OdooRestAPI(prefix='/api/v1')

# controllers/partner.py
from .app import api
from odoo_rest_api import NotFound

@api.get('/partners')
def list_partners(env, **params): ...

@api.get('/partners/{id}')
def get_partner(env, id): ...

# controllers/order.py
from .app import api
from odoo_rest_api import NotFound

@api.get('/orders')
def list_orders(env, **params): ...

@api.get('/orders/{id}')
def get_order(env, id): ...

# controllers/__init__.py — import routes then register
from . import partner
from . import order
from .app import api
api.register()
```

Test:

```bash
curl http://localhost:8069/api/v1/partners
curl http://localhost:8069/api/v1/partners/1
curl http://localhost:8069/api/v1/orders
curl -X POST -H "Content-Type: application/json" \
     -d '{"name": "John Doe", "email": "john@example.com"}' \
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

## Authentication

By default, routes have no authentication (`auth="none"`). You add auth by providing your own handler — a function that takes `request` and returns a `user_id`.

### Option 1: Inline auth handler

```python
from odoo import SUPERUSER_ID, api as odoo_api
from odoo_rest_api import OdooRestAPI, Unauthorized

def my_auth(request):
    api_key = request.httprequest.headers.get('X-API-Key')
    if not api_key:
        raise Unauthorized('Missing X-API-Key header')

    env = odoo_api.Environment(request.env.cr, SUPERUSER_ID, {})
    expected = env['ir.config_parameter'].sudo().get_param('my_api.secret_key')

    if api_key != expected:
        raise Unauthorized('Invalid API key')

    return SUPERUSER_ID  # or a specific user_id

api = OdooRestAPI(prefix='/api/v1', auth_handler=my_auth)
```

### Option 2: Named handler (reusable across multiple APIs)

```python
from odoo_rest_api import register_auth_handler

register_auth_handler('my_key', my_auth)

api = OdooRestAPI(prefix='/api/v1', auth='my_key')
```

### Option 3: Odoo's built-in API keys

```python
from odoo import SUPERUSER_ID, api as odoo_api
from odoo_rest_api import OdooRestAPI, Unauthorized

def odoo_apikey_auth(request):
    api_key = request.httprequest.headers.get('X-API-Key')
    if not api_key:
        raise Unauthorized('Missing X-API-Key header')
    try:
        env = odoo_api.Environment(request.env.cr, SUPERUSER_ID, {})
        uid = env['res.users']._api_key_authenticate(api_key)
    except Exception:
        raise Unauthorized('Invalid API key')
    return uid

api = OdooRestAPI(prefix='/api/v1', auth_handler=odoo_apikey_auth)
```

See [`examples/`](examples/) for a complete working addon with auth and multi-file routing.

## Handler Signature

Handler arguments are injected based on parameter names:

| Parameter | Value |
|---|---|
| `env` | Odoo Environment (authenticated if auth handler provided) |
| `body` | Parsed JSON request body (POST/PUT/PATCH) |
| `{name}` matching path param | Path parameter value (e.g. `id` from `/partners/{id}`) |
| `**params` or `**kwargs` | Remaining query string parameters |
| Named param matching query key | Individual query parameter |

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

## Recordset Serialization

Return recordsets directly — they're auto-converted to dicts via `.read()`:

```python
@api.get('/partners')
def list_partners(env):
    return env['res.partner'].search([])  # Auto-serialized to list of dicts
```

## License

LGPL-3.0
