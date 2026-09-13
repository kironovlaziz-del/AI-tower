"""
Pagination dependency.

Usage:
    @router.get("/", response_model=Page[Foo])
    async def list_foo(
        pagination: PaginationParams = Depends(),
        ...
    ):
        items, total = await service.list_items(..., pagination=pagination)
        return Page(items=items, total=total, skip=pagination.skip, limit=pagination.limit)
"""

from fastapi import Query


class PaginationParams:
    def __init__(
        self,
        skip: int = Query(0, ge=0, description="Number of rows to skip"),
        limit: int = Query(
            50,
            ge=1,
            le=500,
            description="Maximum number of rows to return (1-500)",
        ),
    ):
        self.skip = skip
        self.limit = limit


def make_page(items, total: int, pagination: PaginationParams):
    """Convenience builder used by endpoint functions."""
    from app.schemas.pagination import Page

    return Page(items=items, total=total, skip=pagination.skip, limit=pagination.limit)
