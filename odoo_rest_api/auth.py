import logging

from typing import Callable

from .exceptions import Unauthorized

_logger = logging.getLogger(__name__)

# ── Pluggable auth handler registry ─────────────────────────────
#
# Auth handlers are callables: (request) -> user_id (int)
# Users register their own handlers via register_auth_handler().

_auth_handlers: dict[str, Callable] = {}


def register_auth_handler(name, handler):
    """
    Register an auth handler by name.

    Args:
        name: Handler name used as the ``auth`` parameter
              in ``OdooRestAPI(auth=...)`` or ``@api.get(..., auth=...)``.
        handler: Callable that takes an Odoo ``request`` object and returns
                 the authenticated ``user_id`` (int). Should raise
                 ``Unauthorized`` on failure.

    Example::

        from odoo_rest_api import register_auth_handler, Unauthorized

        def my_api_key_auth(request):
            key = request.httprequest.headers.get("X-API-Key")
            if not key:
                raise Unauthorized("Missing X-API-Key header")
            # your validation logic here...
            return user_id

        register_auth_handler("api_key", my_api_key_auth)
    """
    _auth_handlers[name] = handler
    _logger.debug("Registered auth handler: %s", name)


def get_auth_handler(name):
    """Look up a registered auth handler by name."""
    return _auth_handlers.get(name)


def validate_request(request, auth_mode, auth_handler=None):
    """
    Validate an incoming request.

    Resolution order:
    1. Direct ``auth_handler`` callable (passed via ``OdooRestAPI(auth_handler=...)``)
    2. Registered handler matching ``auth_mode``

    Returns:
        int: The authenticated user_id.

    Raises:
        Unauthorized: If no handler is found or validation fails.
    """
    if auth_handler:
        return auth_handler(request)

    handler = _auth_handlers.get(auth_mode)
    if handler:
        return handler(request)

    raise Unauthorized(
        f"No auth handler registered for '{auth_mode}'. "
        "Provide a custom auth_handler or call register_auth_handler()."
    )


def get_authenticated_env(request, user_id):
    """Build an Odoo Environment bound to the authenticated user."""
    from odoo import api
    return api.Environment(request.env.cr, user_id, request.env.context)
