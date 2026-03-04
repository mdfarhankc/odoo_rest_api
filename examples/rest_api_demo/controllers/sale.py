"""
Sale Order endpoints.

    GET    /api/v1/sales             List sales
    GET    /api/v1/sales/{id}        Get sale order details
"""

from odoo_rest_api.exceptions import NotFound
from .app import api

FIELDS = ["name", "partner_id", "date_order", "amount_total", "state"]
LINE_FIELDS = ["product_id", "name", "product_uom_qty", "price_unit", "price_subtotal"]

@api.get("/sales")
def list_sales(env, **params):
    """ List sales """
    limit = min(int(params.get("limit", 80)), 1000)
    offset = int(params.get("offset", 0))
    state = params.get("state", "")

    domain = [("state", "=", state)] if state else []
    return env["sale.order"].search_read(domain, FIELDS, limit=limit, offset=offset)


@api.get("/sales/{id}")
def get_sale_details(env, id):
    """ Get sale order details """
    order = env["sale.order"].browse(int(id))
    if not order.exists():
        raise NotFound("Order not found")
    data = order.read(FIELDS)[0]
    data["lines"] = order.order_line.read(LINE_FIELDS)
    return data
