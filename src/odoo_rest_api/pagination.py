from dataclasses import dataclass

MAX_LIMIT = 1000
DEFAULT_LIMIT = 80


@dataclass
class PaginationParams:
    """Pagination parameters extracted from request query string."""

    offset: int = 0
    limit: int = DEFAULT_LIMIT

    @classmethod
    def from_params(cls, params: dict) -> "PaginationParams":
        """Extract offset/limit from a params dict, removing them from the dict."""
        offset = int(params.pop("offset", 0))
        limit = min(int(params.pop("limit", DEFAULT_LIMIT)), MAX_LIMIT)
        return cls(offset=max(offset, 0), limit=max(limit, 1))
