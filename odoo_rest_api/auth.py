import logging

from odoo import SUPERUSER_ID, api

from .exceptions import Unauthorized

_logger = logging.getLogger(__name__)

# ── Pluggable auth handler registry ─────────────────────────────
#
# Auth handlers are callables: (request) -> user_id (int)
#
# The default "api_key" handler uses Odoo's built-in API keys
# (res.users.apikeys). The addon `odoo_rest_api_base` can override
# this with a richer handler that adds scopes, rate limiting, etc.

_auth_handlers: dict[str, callable] = {}


def register_auth_handler(name, handler):
    """
    Register an auth handler by name.

    Args:
        name: Handler name (e.g. "api_key"). Used as the ``auth`` parameter
              in ``OdooAPI(auth=...)`` or ``@api.get(..., auth=...)``.
        handler: Callable that takes an Odoo ``request`` object and returns
                 the authenticated ``user_id`` (int). Should raise
                 ``Unauthorized`` on failure.
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
    1. Direct ``auth_handler`` callable (passed via ``OdooAPI(auth_handler=...)``)
    2. Registered handler matching ``auth_mode`` (e.g. from ``odoo_rest_api_base``)
    3. Built-in default for ``"api_key"`` using Odoo's native API keys

    Returns:
        int: The authenticated user_id.

    Raises:
        Unauthorized: If validation fails or no handler is found.
    """
    # 1. Direct handler override
    if auth_handler:
        return auth_handler(request)

    # 2. Registry lookup (addon can override "api_key" with a richer handler)
    handler = _auth_handlers.get(auth_mode)
    if handler:
        return handler(request)

    # 3. Built-in default for "api_key" using Odoo's native system
    if auth_mode == "api_key":
        return _default_api_key_handler(request)

    raise Unauthorized(
        f"No auth handler registered for '{auth_mode}'. "
        "Provide a custom auth_handler or call register_auth_handler()."
    )


def _default_api_key_handler(request):
    """
    Default auth handler using Odoo's built-in API key system.

    Accepts the key via:
      - ``X-API-Key: <key>`` header
      - ``Authorization: Bearer <key>`` header

    Validates against ``res.users.apikeys`` (available in Odoo 14+).
    """
    api_key = request.httprequest.headers.get("X-API-Key")

    if not api_key:
        auth_header = request.httprequest.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            api_key = auth_header[7:]

    if not api_key:
        raise Unauthorized("Missing API key. Use X-API-Key or Authorization: Bearer header.")

    try:
        env = api.Environment(request.env.cr, SUPERUSER_ID, {})
        uid = env["res.users"]._api_key_authenticate(api_key)
    except Exception:
        raise Unauthorized("Invalid API key")

    if not uid:
        raise Unauthorized("Invalid API key")

    return uid


def get_authenticated_env(request, user_id):
    """Build an Odoo Environment bound to the authenticated user."""
    return api.Environment(request.env.cr, user_id, request.env.context)
