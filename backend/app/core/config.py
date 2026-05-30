from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Insurance Operations Platform"
    api_prefix: str = "/api/v1"
    environment: str = "local"
    demo_header_auth_enabled: bool = True
    database_url: str = "postgresql+asyncpg://insurance:insurance@localhost:5434/insurance_ops"
    google_client_id: str = "demo-google-client-id"
    google_callback_url: str = "http://localhost:3002/auth/google/callback"
    google_oauth_scope: str = "openid email profile"
    google_token_verifier_mode: str = "demo"
    openai_ocr_model: str = "gpt-4.1-mini"
    jwt_secret_key: str = "local-dev-change-me"
    jwt_algorithm: str = "HS256"
    access_token_expires_minutes: int = 60
    local_storage_root: str = "uploads"
    max_upload_size_bytes: int = 10 * 1024 * 1024
    storage_provider: str = "local"
    object_storage_bucket: str = ""
    object_storage_endpoint_url: str | None = None
    object_storage_region: str = "us-east-1"
    object_storage_access_key_id: str | None = None
    object_storage_secret_access_key: str | None = None
    storage_download_expires_seconds: int = 300
    worker_batch_size: int = 10
    worker_lock_seconds: int = 60
    worker_max_attempts: int = 3
    worker_retry_backoff_seconds: int = 30
    ai_user_requests_per_minute: int = 10
    ai_tenant_requests_per_minute: int = 60
    ai_max_prompt_chars: int = 4000
    ai_max_retrieved_chunks: int = 5
    ai_max_response_chars: int = 6000
    ai_provider_timeout_seconds: float = 5.0
    ai_max_concurrent_ingest_jobs: int = 3
    core_database_pool_size: int = 10
    core_database_max_overflow: int = 10
    ai_database_pool_size: int = 3
    ai_database_max_overflow: int = 1
    ai_database_pool_timeout_seconds: float = 2.0
    ai_worker_concurrency: int = 2
    ai_retrieval_timeout_seconds: float = 3.0


settings = Settings()
