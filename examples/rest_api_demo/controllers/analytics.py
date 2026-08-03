"""
Analytics & reporting endpoints: complex queries, raw SQL, aggregations.

    GET    /api/v1/analytics/dashboard         Dashboard summary stats
    GET    /api/v1/analytics/top-products       Top selling products (raw SQL)       Stock levels with reorder alerts
"""

from odoo_rest_api.exceptions import BadRequest
from .app import api


@api.get("/analytics/dashboard")
def dashboard(env):
    """Multi-model dashboard that pulls stats from several models in one call."""
    Partner = env["res.partner"]
    Order = env["sale.order"]
    Invoice = env["account.move"]

    total_customers = Partner.search_count([("customer_rank", ">", 0)])
    total_suppliers = Partner.search_count([("supplier_rank", ">", 0)])

    orders_confirmed = Order.search_count([("state", "=", "sale")])
    orders_draft = Order.search_count([("state", "=", "draft")])

    invoices_paid = Invoice.search_count([
        ("move_type", "=", "out_invoice"),
        ("payment_state", "=", "paid"),
    ])
    invoices_pending = Invoice.search_count([
        ("move_type", "=", "out_invoice"),
        ("payment_state", "!=", "paid"),
        ("state", "=", "posted"),
    ])

    return {
        "customers": total_customers,
        "suppliers": total_suppliers,
        "orders": {
            "confirmed": orders_confirmed,
            "draft": orders_draft,
        },
        "invoices": {
            "paid": invoices_paid,
            "pending": invoices_pending,
        },
    }


@api.get("/analytics/top-products")
def top_products(env, **params):
    """
    Top selling products by quantity, using raw SQL for performance.

    Query params:
        limit (int): number of products (default 10)
        period (str): 'month', 'quarter', 'year' (default 'month')
    """
    limit = min(int(params.get("limit", 10)), 100)
    period = params.get("period", "month")

    period_map = {
        "month": "1 month",
        "quarter": "3 months",
        "year": "1 year",
    }
    if period not in period_map:
        raise BadRequest(f"Invalid period '{period}'. Use: month, quarter, year")

    interval = period_map[period]

    env.cr.execute("""
        SELECT
            pt.name->>'en_US'                   AS product_name,
            pp.id                               AS product_id,
            SUM(sol.product_uom_qty)            AS total_qty,
            SUM(sol.price_subtotal)             AS total_revenue,
            COUNT(DISTINCT so.id)               AS order_count
        FROM sale_order_line sol
        JOIN sale_order so ON so.id = sol.order_id
        JOIN product_product pp ON pp.id = sol.product_id
        JOIN product_template pt ON pt.id = pp.product_tmpl_id
        WHERE so.state IN ('sale', 'done')
          AND so.date_order >= NOW() - INTERVAL %s
        GROUP BY pt.name, pp.id
        ORDER BY total_qty DESC
        LIMIT %s
    """, (interval, limit))

    columns = [col.name for col in env.cr.description]
    return [dict(zip(columns, row)) for row in env.cr.fetchall()]
