from hashlib import sha256
from typing import Protocol


class EmbeddingReferenceProvider(Protocol):
    async def create_embedding_ref(self, *, organization_id: str, content: str) -> str:
        """Create or reference an embedding for chunk content."""


class LocalHashEmbeddingReferenceProvider:
    async def create_embedding_ref(self, *, organization_id: str, content: str) -> str:
        digest = sha256(f"{organization_id}:{content}".encode("utf-8")).hexdigest()
        return f"local-hash:{digest}"

