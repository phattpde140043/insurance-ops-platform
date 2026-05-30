from pydantic import BaseModel


class KnowledgeDocumentOut(BaseModel):
    id: str
    organization_id: str
    title: str
    source_type: str
    status: str
    created_at: str


class CreateKnowledgeDocumentIn(BaseModel):
    title: str
    source_type: str = "pdf"


class ChatRequestIn(BaseModel):
    message: str


class ChatResponseOut(BaseModel):
    answer: str
    citations: list[str]
    confidence: float


class KnowledgeIngestOut(BaseModel):
    status: str
    background_job_id: str
    chunk_count: int


class KnowledgeDownloadOut(BaseModel):
    download_url: str
    expires_in: int


class RetrievalSearchIn(BaseModel):
    query: str
    limit: int = 5


class RetrievalChunkOut(BaseModel):
    chunk_id: str
    document_id: str
    content: str
    score: float


class RetrievalSearchOut(BaseModel):
    items: list[RetrievalChunkOut]


class AiPoolStatusOut(BaseModel):
    checked_out: int
    size: int
    overflow: int
    saturated: bool


class AiOperationalTelemetryOut(BaseModel):
    queue_depth: int
    worker_concurrency_limit: int
    provider_calls: int
    average_provider_latency_ms: int
    provider_timeout_count: int
    pool: AiPoolStatusOut
