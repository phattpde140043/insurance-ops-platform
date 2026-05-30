from base64 import urlsafe_b64decode, urlsafe_b64encode
from typing import Generic, Sequence, TypeVar

from fastapi import HTTPException, status
from pydantic import BaseModel, Field

T = TypeVar("T")


class PageInfo(BaseModel):
    next_cursor: str | None = None
    has_next: bool = False


class PaginationMeta(BaseModel):
    limit: int
    sort: str
    next_cursor: str | None = None
    offset: int = 0
    total: int | None = None
    has_more: bool = False


class ListResponse(BaseModel, Generic[T]):
    items: list[T]
    meta: PaginationMeta
    page_info: PageInfo = Field(default_factory=PageInfo)


class StatusResponse(BaseModel):
    status: str


def paginated_response(
    items: Sequence[T],
    *,
    limit: int,
    sort: str,
    offset: int = 0,
    total: int | None = None,
    next_cursor: str | None = None,
) -> dict:
    page_items = list(items[:limit])
    has_more = len(items) > limit
    cursor = next_cursor if has_more else None
    return {
        "items": page_items,
        "meta": {
            "limit": limit,
            "sort": sort,
            "next_cursor": cursor,
            "offset": offset,
            "total": total,
            "has_more": has_more,
        },
        "page_info": {
            "next_cursor": cursor,
            "has_next": has_more,
        },
    }


def encode_offset_cursor(offset: int) -> str:
    return urlsafe_b64encode(str(offset).encode("ascii")).decode("ascii")


def decode_offset_cursor(cursor: str | None) -> int:
    if cursor is None:
        return 0
    try:
        offset = int(urlsafe_b64decode(cursor.encode("ascii")).decode("ascii"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "invalid_cursor",
                "message": "The pagination cursor is invalid.",
            },
        ) from exc
    if offset < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "invalid_cursor",
                "message": "The pagination cursor is invalid.",
            },
        )
    return offset
