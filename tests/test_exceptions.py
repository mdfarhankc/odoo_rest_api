from odoo_rest_api.exceptions import (
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


class TestExceptionDefaults:
    """Each exception should have correct status_code, error_type, and default message."""

    def test_api_exception(self):
        exc = APIException()
        assert exc.status_code == 500
        assert exc.error_type == "ServerError"
        assert exc.message == "Internal Server Error"
        assert exc.details is None

    def test_bad_request(self):
        exc = BadRequest()
        assert exc.status_code == 400
        assert exc.error_type == "BadRequest"
        assert exc.message == "Bad Request"

    def test_unauthorized(self):
        exc = Unauthorized()
        assert exc.status_code == 401
        assert exc.error_type == "Unauthorized"

    def test_forbidden(self):
        exc = Forbidden()
        assert exc.status_code == 403
        assert exc.error_type == "Forbidden"

    def test_not_found(self):
        exc = NotFound()
        assert exc.status_code == 404
        assert exc.error_type == "NotFound"

    def test_method_not_allowed(self):
        exc = MethodNotAllowed()
        assert exc.status_code == 405
        assert exc.error_type == "MethodNotAllowed"

    def test_conflict(self):
        exc = Conflict()
        assert exc.status_code == 409
        assert exc.error_type == "Conflict"

    def test_validation_error(self):
        exc = ValidationError()
        assert exc.status_code == 422
        assert exc.error_type == "ValidationError"

    def test_rate_limit_exceeded(self):
        exc = RateLimitExceeded()
        assert exc.status_code == 429
        assert exc.error_type == "RateLimitExceeded"


class TestExceptionCustomMessage:
    def test_custom_message(self):
        exc = NotFound("Partner not found")
        assert exc.message == "Partner not found"
        assert str(exc) == "Partner not found"

    def test_custom_details(self):
        exc = BadRequest("Validation failed", details={"field": "email"})
        assert exc.message == "Validation failed"
        assert exc.details == {"field": "email"}


class TestExceptionInheritance:
    def test_all_inherit_from_api_exception(self):
        for cls in [
            BadRequest, Unauthorized, Forbidden, NotFound,
            MethodNotAllowed, Conflict, ValidationError, RateLimitExceeded,
        ]:
            assert issubclass(cls, APIException)

    def test_all_inherit_from_exception(self):
        for cls in [
            APIException, BadRequest, Unauthorized, Forbidden, NotFound,
            MethodNotAllowed, Conflict, ValidationError, RateLimitExceeded,
        ]:
            assert issubclass(cls, Exception)

    def test_catchable_as_api_exception(self):
        try:
            raise NotFound("gone")
        except APIException as exc:
            assert exc.status_code == 404
