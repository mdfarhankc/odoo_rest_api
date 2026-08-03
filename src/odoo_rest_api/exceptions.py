class APIException(Exception):
    """Base exception for all REST API errors."""

    status_code = 500
    error_type = "ServerError"

    def __init__(self, message="Internal Server Error", details=None):
        self.message = message
        self.details = details
        super().__init__(message)


class BadRequest(APIException):
    status_code = 400
    error_type = "BadRequest"

    def __init__(self, message="Bad Request", details=None):
        super().__init__(message, details)


class Unauthorized(APIException):
    status_code = 401
    error_type = "Unauthorized"

    def __init__(self, message="Unauthorized", details=None):
        super().__init__(message, details)


class Forbidden(APIException):
    status_code = 403
    error_type = "Forbidden"

    def __init__(self, message="Forbidden", details=None):
        super().__init__(message, details)


class NotFound(APIException):
    status_code = 404
    error_type = "NotFound"

    def __init__(self, message="Not Found", details=None):
        super().__init__(message, details)


class MethodNotAllowed(APIException):
    status_code = 405
    error_type = "MethodNotAllowed"

    def __init__(self, message="Method Not Allowed", details=None):
        super().__init__(message, details)


class Conflict(APIException):
    status_code = 409
    error_type = "Conflict"

    def __init__(self, message="Conflict", details=None):
        super().__init__(message, details)


class ValidationError(APIException):
    status_code = 422
    error_type = "ValidationError"

    def __init__(self, message="Validation Error", details=None):
        super().__init__(message, details)


class RateLimitExceeded(APIException):
    status_code = 429
    error_type = "RateLimitExceeded"

    def __init__(self, message="Rate Limit Exceeded", details=None):
        super().__init__(message, details)
