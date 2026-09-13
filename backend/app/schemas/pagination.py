"""
Generic pagination wrapper shared by all list endpoints.

Response shape:
    {
        "items": [...],
        "total": 123,
        "skip": 0,
        "limit": 50
    }

The frontend unwraps `items` for rendering and uses `total` for the
"showing X of Y" footer / load-more controls.
"""

from typing import Generic, List, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    items: List[T]
    total: int
    skip: int
    limit: int
