from odoo_rest_api.pagination import PaginationParams, DEFAULT_LIMIT, MAX_LIMIT


class TestPaginationParams:
    def test_defaults(self):
        p = PaginationParams()
        assert p.offset == 0
        assert p.limit == DEFAULT_LIMIT

    def test_from_params(self):
        params = {"offset": "10", "limit": "50", "search": "john"}
        p = PaginationParams.from_params(params)
        assert p.offset == 10
        assert p.limit == 50
        # offset and limit should be popped from params
        assert "offset" not in params
        assert "limit" not in params
        # other params should remain
        assert params == {"search": "john"}

    def test_from_params_defaults(self):
        params = {}
        p = PaginationParams.from_params(params)
        assert p.offset == 0
        assert p.limit == DEFAULT_LIMIT

    def test_limit_capped_at_max(self):
        params = {"limit": "9999"}
        p = PaginationParams.from_params(params)
        assert p.limit == MAX_LIMIT

    def test_negative_offset_clamped(self):
        params = {"offset": "-5"}
        p = PaginationParams.from_params(params)
        assert p.offset == 0

    def test_zero_limit_clamped_to_one(self):
        params = {"limit": "0"}
        p = PaginationParams.from_params(params)
        assert p.limit == 1
