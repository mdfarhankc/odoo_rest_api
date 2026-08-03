import inspect
import json

from .exceptions import BadRequest


def parse_request(request, path_kwargs):
    """
    Parse an incoming Odoo HTTP request into a clean dict.

    Returns:
        dict with 'path_params', 'query_params', and 'body' keys.
    """
    parsed = {
        "path_params": dict(path_kwargs),
        "query_params": dict(request.httprequest.args),
        "body": None,
    }

    if request.httprequest.method in ("POST", "PUT", "PATCH"):
        content_type = request.httprequest.content_type or ""
        if "application/json" in content_type:
            try:
                parsed["body"] = json.loads(request.httprequest.data)
            except (json.JSONDecodeError, UnicodeDecodeError) as exc:
                raise BadRequest(f"Invalid JSON body: {exc}")
        else:
            parsed["body"] = dict(request.httprequest.form)

    return parsed


def build_handler_args(handler, env, parsed):
    """
    Inspect the handler's signature and build kwargs to call it.

    Convention:
        - 'env' param  -> Odoo Environment
        - 'body' param -> parsed JSON body
        - named params matching path params -> path param values
        - named params matching query params -> individual query param values
        - **kwargs      -> receives remaining query params
    """
    sig = inspect.signature(handler)
    kwargs = {}
    remaining_query = dict(parsed["query_params"])

    for name, param in sig.parameters.items():
        if name == "env":
            kwargs["env"] = env
        elif name == "body":
            kwargs["body"] = parsed["body"]
        elif name in parsed["path_params"]:
            kwargs[name] = parsed["path_params"][name]
        elif name in remaining_query:
            kwargs[name] = remaining_query.pop(name)

    has_var_keyword = any(
        p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values()
    )
    if has_var_keyword:
        kwargs.update(remaining_query)

    return kwargs
