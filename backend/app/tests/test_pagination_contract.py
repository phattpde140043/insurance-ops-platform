import pytest
from fastapi import HTTPException

from app.domains.shared.schemas import (
    decode_offset_cursor,
    encode_offset_cursor,
    paginated_response,
)


def test_paginated_response_exposes_meta_and_compatibility_page_info() -> None:
    response = paginated_response(
        [{"id": "first"}, {"id": "second"}],
        limit=1,
        sort="-created_at",
        offset=0,
        next_cursor=encode_offset_cursor(1),
    )

    assert response["items"] == [{"id": "first"}]
    assert response["meta"] == {
        "limit": 1,
        "sort": "-created_at",
        "next_cursor": encode_offset_cursor(1),
        "offset": 0,
        "total": None,
        "has_more": True,
    }
    assert response["page_info"]["has_next"] is True


def test_paginated_response_drops_cursor_on_last_page() -> None:
    response = paginated_response(
        [{"id": "only"}],
        limit=1,
        sort="created_at",
        next_cursor=encode_offset_cursor(1),
    )

    assert response["meta"]["next_cursor"] is None
    assert response["meta"]["has_more"] is False


def test_offset_cursor_round_trip() -> None:
    assert decode_offset_cursor(encode_offset_cursor(25)) == 25


@pytest.mark.parametrize("cursor", ["not-base64", encode_offset_cursor(-1)])
def test_invalid_offset_cursor_is_rejected(cursor: str) -> None:
    with pytest.raises(HTTPException) as exc:
        decode_offset_cursor(cursor)

    assert exc.value.status_code == 400
    assert exc.value.detail["code"] == "invalid_cursor"
