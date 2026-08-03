import inspect
from dataclasses import dataclass
from typing import Any, Callable, Optional

# Distinguishes "option not passed" from an explicit None, so that a route
# declaring cors=None (disable CORS here) is not mistaken for "use the default".
_UNSET: Any = object()


@dataclass
class RouteDefinition:
    """Metadata for a single REST route."""

    method: str
    path: str
    handler: Callable
    auth: str = "none"
    cors: Optional[str] = "*"
    tags: Optional[list[str]] = None
    priority: int = 0
    input_model: Optional[type] = None
    output_model: Optional[type] = None


class OdooRestAPI:
    """
    FastAPI-like interface for defining REST endpoints within Odoo.

    Args:
        prefix: URL prefix for all routes (e.g. ``'/api/v1'``).
        auth: Default auth mode for routes (``'none'``, ``'public'``, ``'user'``, or a registered handler name).
        auth_handler: Callable that takes ``request`` and returns ``user_id``.
        cors: Default CORS header value for routes.
        docs: If ``True``, serves Swagger UI at ``{prefix}/docs``.
        title: API title shown in Swagger UI and OpenAPI spec.
        version: API version shown in OpenAPI spec.
        description: API description shown in OpenAPI spec.
        simple_error: If ``True``, error responses return a plain string instead of ``{"type": ..., "message": ...}``.

    Usage::

        from odoo_rest_api import OdooRestAPI

        api = OdooRestAPI(prefix='/api/v1')

        @api.get('/partners')
        def list_partners(env, **params):
            return env['res.partner'].search_read([], ['name', 'email'])

        api.register()
    """

    def __init__(
        self,
        prefix: str = "",
        auth: str = "none",
        auth_handler: Optional[Callable] = None,
        cors: str = "*",
        docs: bool = True,
        title: str = "Odoo REST API",
        version: str = "1.0.0",
        description: str = "",
        simple_error: bool = False,
    ):
        self.prefix = prefix.rstrip("/")
        self.auth = auth
        self.auth_handler = auth_handler
        self.cors = cors
        self.docs = docs
        self.title = title
        self.version = version
        self.description = description
        self.simple_error = simple_error
        self.routes: list[RouteDefinition] = []
        self._controller = None

    # ── HTTP method decorators ──────────────────────────────────────

    def get(self, path: str, **kwargs):
        return self._route("GET", path, **kwargs)

    def post(self, path: str, **kwargs):
        return self._route("POST", path, **kwargs)

    def put(self, path: str, **kwargs):
        return self._route("PUT", path, **kwargs)

    def patch(self, path: str, **kwargs):
        return self._route("PATCH", path, **kwargs)

    def delete(self, path: str, **kwargs):
        return self._route("DELETE", path, **kwargs)

    # ── Route registration ──────────────────────────────────────────

    def _route(
        self,
        method: str,
        path: str,
        *,
        auth: Optional[str] = _UNSET,
        cors: Optional[str] = _UNSET,
        tags: Optional[list[str]] = None,
        priority: int = 0,
        input_model: Optional[type] = None,
        output_model: Optional[type] = None,
    ):
        """Return a decorator that registers a RouteDefinition.

        Options are declared explicitly rather than collected via ``**kwargs``
        so that a misspelled option (``tag=`` for ``tags=``) raises TypeError
        at import time instead of being silently discarded.

        If a route with the same method+path already exists, the one with
        higher ``priority`` wins. On equal priority, the last decorator wins.
        This enables controlled route overriding across addons.

        Usage::

            # Base addon (default priority=0)
            @api.get('/partners')
            def list_partners(env): ...

            # Custom addon (higher priority wins)
            @api.get('/partners', priority=10)
            def list_partners_custom(env): ...
        """

        def decorator(func):
            full_path = self.prefix + "/" + path.lstrip("/")
            route_def = RouteDefinition(
                method=method,
                path=full_path,
                handler=func,
                auth=self.auth if auth is _UNSET else auth,
                cors=self.cors if cors is _UNSET else cors,
                tags=tags,
                priority=priority,
                input_model=input_model,
                output_model=output_model,
            )

            # Replace existing route with same method+path if new priority >= existing
            for i, existing in enumerate(self.routes):
                if existing.method == method and existing.path == full_path:
                    if priority >= existing.priority:
                        self.routes[i] = route_def
                    return func

            self.routes.append(route_def)
            return func

        return decorator

    # ── Controller generation ───────────────────────────────────────

    def register(self):
        """
        Generate an Odoo http.Controller subclass for all registered routes.

        Must be called at **module level** in the consumer addon's controller
        file so that Odoo discovers the controller at import time.

        Example::

            # my_addon/controllers/partner.py
            api = OdooRestAPI(prefix='/api/v1')

            @api.get('/partners')
            def list_partners(env): ...

            api.register()
        """
        from .routing import generate_controller

        caller_frame = inspect.stack()[1]
        caller_module = caller_frame.frame.f_globals["__name__"]

        controller_cls = generate_controller(self, caller_module)

        # Inject into the caller's module namespace so it persists
        caller_frame.frame.f_globals[controller_cls.__name__] = controller_cls
        self._controller = controller_cls
        return controller_cls
