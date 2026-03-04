"""
Sale Order endpoints.

    GET    /api/v1/orders             List orders
    GET    /api/v1/orders/{id}        Get order
"""

from odoo_rest_api import NotFound

from .app import api

FIELDS = ["name", "partner_id", "date_order", "amount_total", "state"]


@api.get("/orders")
def list_orders(env, **params):
    limit = min(int(params.get("limit", 80)), 1000)
    offset = int(params.get("offset", 0))
    state = params.get("state", "")

    domain = [("state", "=", state)] if state else []
    return env["sale.order"].search_read(domain, FIELDS, limit=limit, offset=offset)


@api.get("/orders/{id}")
def get_order(env, id):
    order = env["sale.order"].browse(int(id))
    if not order.exists():
        raise NotFound("Order not found")
    data = order.read(FIELDS)[0]
    data["lines"] = order.order_line.read(
        ["product_id", "name", "product_uom_qty", "price_unit", "price_subtotal"]
    )
    return data
