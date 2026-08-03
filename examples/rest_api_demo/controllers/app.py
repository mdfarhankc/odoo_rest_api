"""
Shared API instance. Import this in all route files.

All routes share the same prefix, auth handler, and CORS config.
"""

from odoo import SUPERUSER_ID, api as odoo_api
from odoo_rest_api import OdooRestAPI
from odoo_rest_api.exceptions import Unauthorized


# ── Auth handler (optional, remove for no auth) ─────────────────
def api_key_auth(request):
    """
    Simple API key auth against ir.config_parameter.

    Setup: create a System Parameter
        key:   rest_api_demo.secret_key
        value: your-secret-key-here
    """
    api_key = request.httprequest.headers.get("X-API-Key")
    if not api_key:
        raise Unauthorized("Missing X-API-Key header")

    env = odoo_api.Environment(request.env.cr, SUPERUSER_ID, {})
    expected = env["ir.config_parameter"].sudo().get_param("rest_api_demo.secret_key")

    if not expected or api_key != expected:
        raise Unauthorized("Invalid API key")

    return SUPERUSER_ID


# ── Shared API instance ─────────────────────────────────────────

# With auth:
# api = OdooRestAPI(prefix="/api/v1", auth_handler=api_key_auth)

# Without auth:
api = OdooRestAPI(
    prefix="/api/v1",
    title="My Odoo API",
    version="1.0.0",
    description="REST API for managing partners and orders",
)
