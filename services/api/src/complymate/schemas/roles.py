from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field


class RoleOut(BaseModel):
    id: UUID
    key: str
    name: str
    description: str | None
    is_system: bool
    permissions: list[str]


class RoleCreate(BaseModel):
    key: str = Field(pattern=r"^[a-z][a-z0-9_]{2,40}$")
    name: str = Field(min_length=2, max_length=120)
    description: str | None = None
    base_role_key: str
    permissions: list[str]


class RoleUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    permissions: list[str] | None = None
