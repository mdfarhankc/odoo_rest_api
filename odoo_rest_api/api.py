import inspect
from dataclasses import dataclass
from typing import Callable, Optional


@dataclass
class RouteDefinition:
    """Metadata for a single REST route."""

    method: str
    path: str
    handler: Callable
    auth: str = "none"
    cors: Optional[str] = "*"
    tags: Optional[list] = None


class OdooRestAPI:
    """
    FastAPI-like interface for defining REST endpoints within Odoo.

    Usage::

        from odoo_rest_api import OdooRestAPI

        api = OdooRestAPI(prefix='/api/v1')

        @api.get('/partners')
        def list_partners(env, **params):
            return env['res.partner'].search_read([], ['name', 'email'])

        api.register()

    Custom auth handler::

        def my_auth(request):
            token = request.httprequest.headers.get('Authorization')
            # ... validate token, return user_id
            return user_id

        api = OdooRestAPI(prefix='/api/v1', auth_handler=my_auth)
    """

    _instances: list = []

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
    ):
        self.prefix = prefix.rstrip("/")
        self.auth = auth
        self.auth_handler = auth_handler
        self.cors = cors
        self.docs = docs
        self.title = title
        self.version = version
        self.description = description
        self.routes: list[RouteDefinition] = []
        self._controller = None
        OdooRestAPI._instances.append(self)

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

    def _route(self, method: str, path: str, **kwargs):
        """Return a decorator that registers a RouteDefinition."""

        def decorator(func):
            route_def = RouteDefinition(
                method=method,
                path=self.prefix + "/" + path.lstrip("/"),
                handler=func,
                auth=kwargs.get("auth", self.auth),
                cors=kwargs.get("cors", self.cors),
                tags=kwargs.get("tags"),
            )
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
