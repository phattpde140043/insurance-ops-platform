from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class PageInfo(BaseModel):
    next_cursor: str | None = None
    has_next: bool = False


class ListResponse(BaseModel, Generic[T]):
    items: list[T]
    page_info: PageInfo = Field(default_factory=PageInfo)


class StatusResponse(BaseModel):
    status: str
