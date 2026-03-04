"""
Partner endpoints.

    GET    /api/v1/partners           List partners
    GET    /api/v1/partners/{id}      Get partner
    POST   /api/v1/partners           Create partner
    PUT    /api/v1/partners/{id}      Update partner
    PATCH  /api/v1/partners/{id}      Partial update
    DELETE /api/v1/partners/{id}      Delete partner
"""

from odoo_rest_api.exceptions import BadRequest, NotFound
from .app import api

FIELDS = ["name", "email", "phone", "street", "city", "country_id", "is_company"]


@api.get("/partners")
def list_partners(env, **params):
    """ Get all partners """
    limit = min(int(params.get("limit", 80)), 1000)
    offset = int(params.get("offset", 0))
    search = params.get("search", "")

    domain = [("name", "ilike", search)] if search else []
    return env["res.partner"].search_read(domain, FIELDS, limit=limit, offset=offset)


@api.get("/partners/{id}")
def get_partner(env, id):
    """ Get partner by id """
    partner = env["res.partner"].browse(int(id))
    if not partner.exists():
        raise NotFound("Partner not found")
    return partner.read(FIELDS)[0]


@api.post("/partners")
def create_partner(env, body):
    """ Create partner """
    if not body or not body.get("name"):
        raise BadRequest("'name' is required")
    partner = env["res.partner"].create(body)
    return partner.read(FIELDS)[0]


@api.put("/partners/{id}")
def update_partner(env, id, body):
    """ Update partner """
    partner = env["res.partner"].browse(int(id))
    if not partner.exists():
        raise NotFound("Partner not found")
    if not body:
        raise BadRequest("Request body is required")
    partner.write(body)
    return partner.read(FIELDS)[0]


@api.patch("/partners/{id}")
def patch_partner(env, id, body):
    """ Patch partner """
    partner = env["res.partner"].browse(int(id))
    if not partner.exists():
        raise NotFound("Partner not found")
    if not body:
        raise BadRequest("Request body is required")
    partner.write(body)
    return partner.read(FIELDS)[0]


@api.delete("/partners/{id}")
def delete_partner(env, id):
    """ Delete partner """
    partner = env["res.partner"].browse(int(id))
    if not partner.exists():
        raise NotFound("Partner not found")
    partner.unlink()
    return {"deleted": True}
