"""
Purchase Order endpoints.

    GET    /api/v1/purchases             List purchases
    GET    /api/v1/purchases/{id}        Get purchase order details
"""

from odoo_rest_api.exceptions import NotFound
from .app import api

FIELDS = ["name", "partner_id", "date_order", "amount_total", "state"]
LINE_FIELDS = ["product_id", "name", "product_uom_qty", "price_unit", "price_subtotal"]


@api.get("/purchases")
def list_purchases(env, **params):
    """ List purchases """
    limit = min(int(params.get("limit", 80)), 1000)
    offset = int(params.get("offset", 0))
    state = params.get("state", "")

    domain = [("state", "=", state)] if state else []
    return env["purchase.order"].search_read(domain, FIELDS, limit=limit, offset=offset)


@api.get("/purchases/{id}")
def get_purchase_details(env, id):
    """ Get purchase order details """
    order = env["purchase.order"].browse(int(id))
    if not order.exists():
        raise NotFound("Order not found")
    data = order.read(FIELDS)[0]
    data["lines"] = order.order_line.read(LINE_FIELDS)
    return data
