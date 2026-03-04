import logging

from odoo import SUPERUSER_ID, http

from .auth import get_authenticated_env, validate_request
from .exceptions import APIException
from .request_utils import build_handler_args, parse_request
from .response import error_response, success_response

_logger = logging.getLogger(__name__)


def make_handler(route_def, auth_handler=None):
    """
    Create an Odoo controller method that wraps a user-defined handler.

    The wrapper:
    1. Validates auth (via pluggable handler or registry lookup)
    2. Parses request body / query / path params
    3. Calls the user's handler with (env, body, path params, query params)
    4. Wraps the result in a standardized JSON response
    5. Catches APIExceptions and returns error responses
    """
    user_handler = route_def.handler
    auth_mode = route_def.auth

    def controller_method(self, **kwargs):
        try:
            request = http.request

            # Authentication
            if auth_mode in ("none", "public", "user"):
                if auth_mode == "user":
                    env = request.env
                else:
                    env = request.env(user=SUPERUSER_ID)
            else:
                # Pluggable auth: use direct handler or registry lookup
                user_id = validate_request(request, auth_mode, auth_handler)
                env = get_authenticated_env(request, user_id)

            # Parse request
            parsed = parse_request(request, kwargs)

            # Build handler arguments from signature
            call_kwargs = build_handler_args(user_handler, env, parsed)

            # Call user handler
            result = user_handler(**call_kwargs)

            # If the handler returned a raw werkzeug Response, pass it through
            from werkzeug.wrappers import Response as WerkzeugResponse

            if isinstance(result, WerkzeugResponse):
                return result

            return success_response(result)

        except APIException as exc:
            return error_response(
                message=exc.message,
                status=exc.status_code,
                error_type=exc.error_type,
                details=exc.details,
            )
        except Exception:
            _logger.exception("Unhandled exception in REST handler %s", user_handler.__name__)
            return error_response("Internal Server Error", status=500)

    controller_method.__name__ = user_handler.__name__
    return controller_method


def generate_controller(api_instance, caller_module):
    """
    Dynamically create an http.Controller subclass with @http.route()
    methods for every route registered on the OdooAPI instance.

    The controller's __module__ is set to caller_module so Odoo registers
    it under the correct addon.
    """
    methods = {"__module__": caller_module}

    for i, route_def in enumerate(api_instance.routes):
        method_name = f"_rest_{i}_{route_def.handler.__name__}"

        # Convert {param} to <param> for werkzeug routing
        odoo_path = route_def.path.replace("{", "<").replace("}", ">")

        handler = make_handler(route_def, auth_handler=api_instance.auth_handler)

        decorated = http.route(
            odoo_path,
            type="http",
            auth="none",
            methods=[route_def.method],
            csrf=False,
            cors=route_def.cors,
        )(handler)

        methods[method_name] = decorated

    # Catch-all route: returns JSON 404 for any unmatched path under the prefix
    if api_instance.prefix:
        catchall_path = api_instance.prefix + "/<path:unmatched>"

        def catchall_handler(self, **kwargs):
            return error_response(
                message=f"Endpoint not found: {http.request.httprequest.path}",
                status=404,
                error_type="NotFound",
            )

        catchall_handler.__name__ = "_rest_catchall"
        decorated_catchall = http.route(
            catchall_path,
            type="http",
            auth="none",
            methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
            csrf=False,
        )(catchall_handler)
        methods["_rest_catchall"] = decorated_catchall

    controller_name = f"RestController_{id(api_instance)}"
    controller_cls = type(controller_name, (http.Controller,), methods)
    return controller_cls
