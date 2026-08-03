# How odoo-rest-api Works: A Deep Dive

This document explains how the `odoo-rest-api` library works under the hood, the problems it solves, and the design decisions behind every module.

---

## Table of Contents

- [The Problem](#the-problem)
- [The Solution](#the-solution)
- [Project Structure](#project-structure)
- [How It Works: Step by Step](#how-it-works-step-by-step)
  - [Step 1: Defining Routes (api.py)](#step-1-defining-routes-apipy)
  - [Step 2: Registering with Odoo (api.py → routing.py)](#step-2-registering-with-odoo-apipy--routingpy)
  - [Step 3: Dynamic Controller Generation (routing.py)](#step-3-dynamic-controller-generation-routingpy)
  - [Step 4: Handling Incoming Requests (routing.py → request_utils.py)](#step-4-handling-incoming-requests-routingpy--request_utilspy)
  - [Step 5: Signature-Based Argument Injection (request_utils.py)](#step-5-signature-based-argument-injection-request_utilspy)
  - [Step 6: Response Formatting (response.py)](#step-6-response-formatting-responsepy)
  - [Step 7: Error Handling (exceptions.py)](#step-7-error-handling-exceptionspy)
  - [Step 8: Authentication (auth.py)](#step-8-authentication-authpy)
  - [Step 9: Auto-Generated API Docs (docs.py)](#step-9-auto-generated-api-docs-docspy)
- [Key Technical Challenges We Solved](#key-technical-challenges-we-solved)
- [Design Decisions](#design-decisions)

---

## The Problem

Creating REST APIs in Odoo using the built-in `http.Controller` is verbose and lacks modern conventions:

```python
# The old way, every endpoint looks like this
from odoo import http
import json

class PartnerAPI(http.Controller):

    @http.route('/api/v1/partners', type='http', auth='none',
                methods=['GET'], csrf=False, cors='*')
    def get_partners(self, **kwargs):
        try:
            request = http.request
            partners = request.env['res.partner'].sudo().search_read(
                [], ['name', 'email'], limit=80
            )
            return request.make_json_response({
                'success': True,
                'data': partners,
            })
        except Exception as e:
            return request.make_json_response({
                'success': False,
                'error': str(e),
            }, status=500)

    @http.route('/api/v1/partners/<int:id>', type='http', auth='none',
                methods=['GET'], csrf=False, cors='*')
    def get_partner(self, id, **kwargs):
        # ... same boilerplate again ...

    @http.route('/api/v1/partners', type='http', auth='none',
                methods=['POST'], csrf=False, cors='*')
    def create_partner(self, **kwargs):
        body = json.loads(http.request.httprequest.data)
        # ... same boilerplate again ...
```

**Pain points:**
- Repeat `@http.route(... type='http', auth='none', csrf=False, cors='*')` on every single endpoint
- Manual `json.loads(request.httprequest.data)` for parsing POST bodies
- No consistent response format, each developer does it differently
- Unhandled exceptions return HTML error pages instead of JSON
- Returning Odoo recordsets crashes with serialization errors (datetime, bytes, etc.)
- No automatic API documentation
- Binary fields (images, files) cause `TypeError: Object of type bytes is not JSON serializable`

## The Solution

```python
# The new way
from odoo_rest_api import OdooRestAPI, NotFound

api = OdooRestAPI(prefix='/api/v1')

@api.get('/partners')
def list_partners(env, **params):
    return env['res.partner'].search([])  # Just return recordsets directly

@api.get('/partners/{id}')
def get_partner(env, id):
    partner = env['res.partner'].browse(int(id))
    if not partner.exists():
        raise NotFound('Partner not found')
    return partner

@api.post('/partners')
def create_partner(env, body):
    return env['res.partner'].create(body)

api.register()
```

Visit `/api/v1/docs` and you get interactive Swagger UI documentation, automatically.

---

## Project Structure

```
odoo_rest_api/
├── __init__.py         # Public API surface: what users import
├── api.py              # OdooRestAPI class, decorators, route collection
├── routing.py          # Dynamic Controller generation (the core trick)
├── request_utils.py    # Request parsing and signature-based arg injection
├── response.py         # Standardized JSON responses + recordset serialization
├── exceptions.py       # Exception hierarchy → HTTP status codes
├── auth.py             # Pluggable authentication registry
├── pagination.py       # PaginationParams helper
└── docs.py             # OpenAPI spec generation + Swagger UI
```

Each file has a single responsibility. No file imports `odoo` at the top level except `routing.py` (which only runs inside Odoo). This means the library can be tested with pytest without a running Odoo instance.

---

## How It Works: Step by Step

### Step 1: Defining Routes (api.py)

When a developer writes `@api.get('/partners')`, here's what happens:

```python
# What the developer writes:
api = OdooRestAPI(prefix='/api/v1')

@api.get('/partners')
def list_partners(env, **params):
    return env['res.partner'].search([])
```

**Under the hood:**

The `@api.get('/partners')` decorator calls `api._route("GET", "/partners")`, which returns a decorator function. That decorator:

1. Creates a `RouteDefinition` dataclass holding the method, full path (`/api/v1/partners`), the handler function reference, auth mode, and CORS setting
2. Appends it to `api.routes` (a simple list)
3. Returns the **original function unchanged**: the decorator doesn't wrap anything

```python
@dataclass
class RouteDefinition:
    method: str           # "GET", "POST", etc.
    path: str             # "/api/v1/partners"
    handler: Callable     # The user's function
    auth: str = "none"    # Authentication mode
    cors: Optional[str] = "*"
    tags: Optional[list] = None  # For Swagger UI grouping
```

At this point, nothing has happened in Odoo yet. We're just collecting metadata. The functions are plain Python functions with no Odoo dependency needed.

### Step 2: Registering with Odoo (api.py → routing.py)

The magic happens when `api.register()` is called:

```python
def register(self):
    from .routing import generate_controller

    caller_frame = inspect.stack()[1]
    caller_module = caller_frame.frame.f_globals["__name__"]

    controller_cls = generate_controller(self, caller_module)

    caller_frame.frame.f_globals[controller_cls.__name__] = controller_cls
    self._controller = controller_cls
    return controller_cls
```

**Two critical things happen here:**

1. **`inspect.stack()[1]`**: We look at who called `register()`. If it's called from `my_addon/controllers/__init__.py`, we get the module name `my_addon.controllers`. This is crucial because Odoo needs to know which addon owns the controller.

2. **Inject into caller's namespace**: After generating the controller class, we inject it into the caller's module globals. This makes it persist and be discoverable by Odoo's module loader.

**Why must `register()` be called at module level?**

Odoo discovers controllers at import time. When Odoo loads an addon, it imports all Python files and looks for `http.Controller` subclasses. If `register()` is called inside a function or lazily, Odoo won't find the controller. That's why the pattern is:

```python
# controllers/__init__.py
from . import partner    # Decorators run, routes collected
from . import order      # More routes collected
from .app import api
api.register()           # Controller generated NOW, at import time
```

### Step 3: Dynamic Controller Generation (routing.py)

This is the most important file in the library. It bridges the gap between our decorator API and Odoo's controller system.

```python
def generate_controller(api_instance, caller_module):
    methods = {"__module__": caller_module}

    for i, route_def in enumerate(api_instance.routes):
        method_name = f"_rest_{i}_{route_def.handler.__name__}"
        odoo_path = route_def.path.replace("{", "<").replace("}", ">")

        handler = make_handler(route_def, auth_handler=api_instance.auth_handler)

        decorated = http.route(
            odoo_path, type="http", auth="none",
            methods=[route_def.method], csrf=False, cors=route_def.cors,
        )(handler)

        methods[method_name] = decorated

    controller_name = f"RestController_{id(api_instance)}"
    controller_cls = type(controller_name, (http.Controller,), methods)
    return controller_cls
```

**Breaking this down:**

1. **`methods = {"__module__": caller_module}`**: This dict will become the class body. Setting `__module__` is critical: Odoo's controller metaclass reads this to register the controller under the correct addon. Without this, Odoo wouldn't know which addon owns these routes.

2. **Path conversion**: Our user-friendly `{id}` syntax is converted to werkzeug's `<id>` syntax: `/api/v1/partners/{id}` → `/api/v1/partners/<id>`

3. **`make_handler()`**: Wraps the user's simple function in a full Odoo controller method that handles auth, request parsing, response formatting, and error catching (explained in Step 4).

4. **`http.route()`**: Each wrapped handler is decorated with Odoo's route decorator. We always use `auth="none"` because the library handles authentication itself.

5. **`type(name, (http.Controller,), methods)`**: This is Python's dynamic class creation. It's equivalent to writing a class definition, but at runtime. We create a class that:
   - Inherits from `http.Controller`
   - Has the correct `__module__`
   - Contains all our route methods

**Catch-all 404 route:**

```python
if api_instance.prefix:
    catchall_path = api_instance.prefix + "/<path:unmatched>"
    # Returns JSON 404 for any unmatched path under the prefix
```

Without this, hitting `/api/v1/nonexistent` would return Odoo's default HTML 404 page. The catch-all ensures all unmatched API paths return a proper JSON error.

### Step 4: Handling Incoming Requests (routing.py → request_utils.py)

When a request comes in, here's the flow inside `make_handler()`:

```python
def make_handler(route_def, auth_handler=None):
    user_handler = route_def.handler
    auth_mode = route_def.auth

    def controller_method(self, **kwargs):
        try:
            request = http.request

            # 1. Authentication
            if auth_mode in ("none", "public", "user"):
                if auth_mode == "user":
                    env = request.env
                else:
                    env = request.env(user=SUPERUSER_ID)
            else:
                user_id = validate_request(request, auth_mode, auth_handler)
                env = get_authenticated_env(request, user_id)

            # 2. Parse request (body, query params, path params)
            parsed = parse_request(request, kwargs)

            # 3. Build handler arguments from function signature
            call_kwargs = build_handler_args(user_handler, env, parsed)

            # 4. Call the user's function
            result = user_handler(**call_kwargs)

            # 5. Return standardized response
            return success_response(result)

        except APIException as exc:
            return error_response(exc.message, exc.status_code, exc.error_type, exc.details)
        except Exception:
            return error_response("Internal Server Error", status=500)

    return controller_method
```

**The `env` problem:**

When `auth="none"`, Odoo's `request.env` has no user, it's an empty recordset. Calling `request.env['res.partner'].search([])` would crash with a singleton error. We solve this by using `request.env(user=SUPERUSER_ID)`, which gives us a usable environment bound to the admin user.

### Step 5: Signature-Based Argument Injection (request_utils.py)

This is what gives the library its FastAPI-like feel. Instead of the developer manually extracting parameters, we inspect their function signature and inject the right values.

```python
def build_handler_args(handler, env, parsed):
    sig = inspect.signature(handler)
    kwargs = {}
    remaining_query = dict(parsed["query_params"])

    for name, param in sig.parameters.items():
        if name == "env":
            kwargs["env"] = env
        elif name == "body":
            kwargs["body"] = parsed["body"]
        elif name in parsed["path_params"]:
            kwargs[name] = parsed["path_params"][name]
        elif name in remaining_query:
            kwargs[name] = remaining_query.pop(name)

    # If handler has **kwargs, pass remaining query params
    has_var_keyword = any(
        p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values()
    )
    if has_var_keyword:
        kwargs.update(remaining_query)

    return kwargs
```

**How it works with an example:**

```python
# User writes:
@api.get('/partners/{id}')
def get_partner(env, id):
    ...

# Request: GET /api/v1/partners/42?fields=name,email
# Signature inspection finds: env, id
# env → Odoo Environment
# id → matched from path params (value: "42")
# fields → not in signature, ignored (unless **kwargs present)
```

```python
# User writes:
@api.get('/partners')
def list_partners(env, limit: int = 80, **params):
    ...

# Request: GET /api/v1/partners?limit=10&search=alice
# limit → matched from query params (value: "10")
# **params → receives remaining: {"search": "alice"}
```

**Request body parsing** happens in `parse_request()`:
- POST/PUT/PATCH with `Content-Type: application/json` → `json.loads(request.httprequest.data)`
- POST with form data → `dict(request.httprequest.form)`
- GET/DELETE → no body parsing

### Step 6: Response Formatting (response.py)

Every response follows the same format:

```json
// Success
{"success": true, "data": [...], "error": null}

// Error
{"success": false, "data": null, "error": {"type": "NotFound", "message": "Partner not found"}}
```

**Automatic recordset serialization:**

The developer can return an Odoo recordset directly:

```python
@api.get('/partners')
def list_partners(env):
    return env['res.partner'].search([])  # Returns a recordset
```

The library detects recordsets using duck typing (checks for `_name`, `ids`, and `read` attributes, without importing Odoo's model classes):

```python
def _is_recordset(obj):
    return hasattr(obj, "_name") and hasattr(obj, "ids") and hasattr(obj, "read")
```

If a recordset is detected, it's automatically converted to a list of dicts via `.read()`. This is recursive, so nested recordsets (like Many2many fields) are also serialized.

**Custom JSON serializer** handles types that `json.dumps` can't:
- `datetime` → ISO format string (`"2026-03-04T12:30:00"`)
- `date` → ISO format string (`"2026-03-04"`)
- `bytes` → UTF-8 string, or base64 if not valid UTF-8 (handles Odoo binary fields like images)

### Step 7: Error Handling (exceptions.py)

An exception hierarchy maps to HTTP status codes:

```
APIException (500)
├── BadRequest (400)
├── Unauthorized (401)
├── Forbidden (403)
├── NotFound (404)
├── MethodNotAllowed (405)
├── Conflict (409)
├── ValidationError (422)
└── RateLimitExceeded (429)
```

When a handler raises any `APIException`, the wrapper in `make_handler()` catches it and returns a proper JSON error response with the correct HTTP status code. Unhandled exceptions (anything not an `APIException`) return a generic 500 error. The actual traceback is logged server-side but never exposed to the client.

### Step 8: Authentication (auth.py)

The library ships with **no built-in auth**: by default, all routes are public (`auth="none"`). This is intentional: authentication requirements vary wildly between projects (API keys, JWT, OAuth, Odoo's built-in keys, etc.).

Instead, auth is fully pluggable via two patterns:

**Pattern 1: Inline handler**
```python
def my_auth(request):
    key = request.httprequest.headers.get('X-API-Key')
    if not key:
        raise Unauthorized('Missing API key')
    # Validate and return user_id
    return user_id

api = OdooRestAPI(prefix='/api/v1', auth_handler=my_auth)
```

**Pattern 2: Named registry**
```python
register_auth_handler('api_key', my_auth)
api = OdooRestAPI(prefix='/api/v1', auth='api_key')
```

The registry pattern is useful when multiple API instances share the same auth logic. The handler is a simple function: takes `request`, returns `user_id` (int), raises `Unauthorized` on failure.

**Lazy imports:** `auth.py` imports `from odoo import api` only inside `get_authenticated_env()`, not at module level. This allows the library to be imported and tested without Odoo installed.

### Step 9: Auto-Generated API Docs (docs.py)

Visit `/api/v1/docs` and you get a full Swagger UI, automatically generated from your registered routes.

**How the spec is built:**

At `register()` time (not per-request), the library generates an OpenAPI 3.0 spec by:

1. **Iterating all routes** and for each one:
   - Extracting path parameters from `{param}` syntax using regex
   - Inspecting the handler's function signature for query parameters (skipping `env`, `body`, path params, and `**kwargs`)
   - Reading type hints and mapping them to OpenAPI types (`int` → `"integer"`, `str` → `"string"`, etc.)
   - Parsing the docstring: first line becomes the summary, rest becomes the description
   - Auto-deriving tags from the handler's `__module__` (e.g., functions in `partner.py` get tagged as `"partner"`)
   - Adding request body schema for POST/PUT/PATCH methods
   - Adding security requirements if auth is configured

2. **Caching the result**: The spec JSON is generated once and stored as a string. The `/openapi.json` endpoint just returns this cached string. No computation per request.

3. **Serving Swagger UI**: The `/docs` endpoint returns an HTML page that loads Swagger UI from a CDN (unpkg.com) and points it at the `/openapi.json` endpoint.

---

## Key Technical Challenges We Solved

### 1. Odoo's Controller Discovery

Odoo discovers controllers by scanning for `http.Controller` subclasses at import time. The metaclass (or `__init_subclass__` in newer Odoo) reads `__module__` from the class to determine which addon owns it. Our dynamic `type()` call must set `__module__` correctly. Otherwise Odoo either ignores the controller or registers it under the wrong addon.

### 2. The `env` Singleton Problem

With `auth='none'`, Odoo's `request.env` has no user, so `request.env.user` is an empty recordset. Any ORM operation would crash:
```
ValueError: Expected singleton: res.users()
```
Solution: Use `request.env(user=SUPERUSER_ID)` to get a proper environment bound to the admin user.

### 3. Bytes Serialization

Odoo binary fields (images, PDF attachments) are returned as `bytes`. Python's `json.dumps()` can't serialize bytes:
```
TypeError: Object of type bytes is not JSON serializable
```
Solution: The custom JSON serializer tries UTF-8 decoding first, then falls back to base64 encoding.

### 4. Testing Without Odoo

The library imports Odoo internals (`from odoo import http`), but we want to run pytest without a full Odoo installation. Solution:
- All `odoo` imports are either in `routing.py` (which only runs inside Odoo) or lazy (inside function bodies, like `auth.py`)
- Test files mock `werkzeug` with a minimal `_FakeResponse` class
- Tests exercise route collection, spec generation, serialization, and exception handling, all without Odoo

### 5. Multi-File API Support

Users want to split routes across files (`partner.py`, `order.py`, `analytics.py`). The challenge: all files need to share one `OdooRestAPI` instance, and `register()` must be called only once, after all routes are imported.

Solution: The shared instance pattern:
```python
# app.py: defines the instance
api = OdooRestAPI(prefix='/api/v1')

# partner.py: imports and uses it
from .app import api
@api.get('/partners')
def list_partners(env): ...

# __init__.py: imports all routes, then registers
from . import partner
from . import order
from .app import api
api.register()  # All routes now collected, generate one controller
```

The import order in `__init__.py` matters: route files first (to run decorators), then `register()`.

---

## Design Decisions

**Why `auth='none'` on all Odoo routes?**
We always tell Odoo `auth='none'` on the generated controller methods. The library handles auth itself in the `make_handler()` wrapper. This gives us full control over the auth flow and error responses (JSON instead of Odoo's HTML redirects).

**Why no built-in auth?**
Every Odoo project has different auth requirements. Forcing a specific approach (API keys, JWT, etc.) would either be too restrictive or too complex. Instead, auth is a simple function: `request → user_id`. Developers implement exactly what they need.

**Why dynamic class creation via `type()` instead of a base class?**
If we used a base class (`class MyAPI(OdooRestController)`), the developer would still need to write methods and apply `@http.route()`. Dynamic class creation means the developer writes plain functions and we generate the entire controller class. This is what enables the decorator-based API.

**Why pip package instead of Odoo addon?**
Odoo addons must be in the `addons_path`. A pip package can be installed anywhere and `import`ed by any addon. This means:
- Install with `pip install odoo-rest-api`
- No addon dependency in `__manifest__.py`
- Works across Odoo 16, 17, and 18 without version-specific addon manifests

**Why cache the OpenAPI spec at registration time?**
Routes are fixed at import time and never change while the server is running. Generating the spec once (instead of per-request) is both simpler and faster.
