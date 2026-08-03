from importlib.metadata import PackageNotFoundError, version as _get_version

from .api import OdooRestAPI
from .auth import register_auth_handler
from .docs import generate_openapi_spec
from .exceptions import (
    APIException,
    BadRequest,
    Conflict,
    Forbidden,
    MethodNotAllowed,
    NotFound,
    RateLimitExceeded,
    Unauthorized,
    ValidationError,
)
from .pagination import PaginationParams
from .response import error_response, success_response

try:
    __version__ = _get_version("odoo-rest-api")
except PackageNotFoundError:
    # Running from a source tree without an install; no distribution metadata.
    __version__ = "0.0.0.dev0"

__all__ = [
    "APIException",
    "BadRequest",
    "Conflict",
    "Forbidden",
    "MethodNotAllowed",
    "NotFound",
    "OdooRestAPI",
    "PaginationParams",
    "RateLimitExceeded",
    "Unauthorized",
    "ValidationError",
    "__version__",
    "error_response",
    "generate_openapi_spec",
    "register_auth_handler",
    "success_response",
]
