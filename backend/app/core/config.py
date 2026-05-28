from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Insurance Operations Platform"
    api_prefix: str = "/api/v1"
    environment: str = "local"
    demo_header_auth_enabled: bool = True
    database_url: str = "postgresql+asyncpg://insurance:insurance@localhost:5434/insurance_ops"
    google_client_id: str = "demo-google-client-id"
    google_oauth_scope: str = "openid email profile"
    google_token_verifier_mode: str = "demo"
    openai_ocr_model: str = "gpt-4.1-mini"
    jwt_secret_key: str = "local-dev-change-me"
    jwt_algorithm: str = "HS256"
    access_token_expires_minutes: int = 60
    local_storage_root: str = "uploads"
    max_upload_size_bytes: int = 10 * 1024 * 1024


settings = Settings()
