from io import BytesIO

import pytest
from fastapi import HTTPException

from app.core import storage


class FakeS3Client:
    def __init__(self) -> None:
        self.objects: dict[tuple[str, str], bytes] = {}

    def put_object(self, *, Bucket: str, Key: str, Body: bytes) -> None:
        self.objects[(Bucket, Key)] = Body

    def get_object(self, *, Bucket: str, Key: str) -> dict:
        return {"Body": BytesIO(self.objects[(Bucket, Key)])}

    def delete_object(self, *, Bucket: str, Key: str) -> None:
        self.objects.pop((Bucket, Key), None)

    def generate_presigned_url(
        self, operation: str, *, Params: dict, ExpiresIn: int
    ) -> str:
        return (
            f"https://storage.example/{operation}/{Params['Bucket']}/{Params['Key']}"
            f"?expires={ExpiresIn}"
        )


@pytest.mark.asyncio
async def test_local_storage_provider_round_trip(tmp_path) -> None:
    provider = storage.LocalStorageProvider(str(tmp_path))

    await provider.put_bytes("org/file/document.pdf", b"pdf-content")

    assert await provider.get_bytes("org/file/document.pdf") == b"pdf-content"
    assert (
        await provider.create_download_url("org/file/document.pdf", expires_seconds=60)
        is None
    )


@pytest.mark.asyncio
async def test_s3_storage_provider_uses_private_presigned_url(monkeypatch) -> None:
    monkeypatch.setattr(storage.settings, "object_storage_bucket", "insurance-private")
    client = FakeS3Client()
    provider = storage.S3StorageProvider(client=client)

    await provider.put_bytes("org/file/document.pdf", b"pdf-content")

    assert await provider.get_bytes("org/file/document.pdf") == b"pdf-content"
    assert await provider.create_download_url(
        "org/file/document.pdf", expires_seconds=300
    ) == (
        "https://storage.example/get_object/insurance-private/org/file/document.pdf"
        "?expires=300"
    )


def test_storage_download_token_round_trip() -> None:
    token = storage.issue_storage_download_token(
        organization_id="org_demo",
        storage_key="org_demo/file/document.pdf",
        expires_seconds=300,
    )

    assert storage.verify_storage_download_token(token) == (
        "org_demo",
        "org_demo/file/document.pdf",
    )


def test_invalid_storage_download_token_is_rejected() -> None:
    with pytest.raises(HTTPException) as exc:
        storage.verify_storage_download_token("not-a-valid-token")

    assert exc.value.status_code == 401
    assert exc.value.detail["code"] == "invalid_download_token"


def test_expired_storage_download_token_is_rejected() -> None:
    token = storage.issue_storage_download_token(
        organization_id="org_demo",
        storage_key="org_demo/file/document.pdf",
        expires_seconds=-1,
    )

    with pytest.raises(HTTPException) as exc:
        storage.verify_storage_download_token(token)

    assert exc.value.status_code == 401


def test_unknown_storage_provider_fails_closed(monkeypatch) -> None:
    monkeypatch.setattr(storage.settings, "storage_provider", "typo")

    with pytest.raises(HTTPException) as exc:
        storage.get_storage_provider()

    assert exc.value.status_code == 503
    assert exc.value.detail["code"] == "invalid_storage_provider"
