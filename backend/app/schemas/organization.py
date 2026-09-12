import re
from pydantic import BaseModel, field_validator
from datetime import datetime

SLUG_PATTERN = re.compile(r"^[a-z0-9](?:[a-z0-9-]{1,61}[a-z0-9])?$")


class OrganizationBase(BaseModel):
    name: str
    plan: str = "free"


class OrganizationCreate(OrganizationBase):
    pass


class OrganizationOut(OrganizationBase):
    id: int
    slug: str
    created_at: datetime

    class Config:
        from_attributes = True


class SlugMixin(BaseModel):
    """Shared slug validation for register and any future endpoints."""
    slug: str

    @field_validator("slug")
    @classmethod
    def _validate_slug(cls, v: str) -> str:
        v = v.strip().lower()
        if not SLUG_PATTERN.match(v):
            raise ValueError(
                "slug must be 3-63 chars, lowercase letters, digits and hyphens "
                "(must start and end with a letter or digit)"
            )
        return v
