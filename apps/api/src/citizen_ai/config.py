from functools import lru_cache
from hashlib import sha256
from typing import Literal

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    app_env: Literal["local", "test", "staging", "production"] = "local"
    app_public_url: str = "http://localhost:8080"
    database_url: SecretStr = SecretStr("")
    migration_database_url: SecretStr = SecretStr("")
    redis_url: SecretStr = SecretStr("redis://redis:6379/0")
    session_secret: SecretStr = SecretStr("")
    cookie_secure: bool = False
    ai_provider: Literal["mock", "openai"] = "mock"
    openai_api_key: SecretStr = SecretStr("")
    openai_chat_model: str = ""
    ai_request_timeout_seconds: int = 60
    ai_max_output_tokens: int = 2500
    s3_endpoint: str = "http://minio:9000"
    s3_access_key_id: SecretStr = SecretStr("")
    s3_secret_access_key: SecretStr = SecretStr("")
    s3_bucket: str = "ai-citizen-private"
    max_upload_mb: int = Field(default=25, ge=1, le=25)
    max_upload_files_per_batch: int = Field(default=10, ge=1, le=10)
    clamav_host: str = "clamav"
    clamav_port: int = Field(default=3310, ge=1, le=65535)
    scanner_timeout_seconds: int = Field(default=60, ge=1, le=300)
    parser_url: str = "http://parser:8100"
    extraction_timeout_seconds: int = Field(default=180, ge=5, le=600)
    embedding_provider: Literal["disabled", "openai", "mock"] = "disabled"
    openai_embedding_model: str = ""
    embedding_dimensions: int = Field(default=0, ge=0, le=4096)
    embedding_profile_id: str = ""

    @model_validator(mode="after")
    def safe_configuration(self) -> "Settings":
        if len(self.session_secret.get_secret_value()) < 32:
            raise ValueError("SESSION_SECRET phải có ít nhất 32 ký tự ngẫu nhiên.")
        if not self.database_url.get_secret_value().startswith("postgresql+psycopg://"):
            raise ValueError("DATABASE_URL phải dùng PostgreSQL/psycopg.")
        if self.ai_provider == "openai" and (
            not self.openai_api_key.get_secret_value() or not self.openai_chat_model
        ):
            raise ValueError("Developer cần cấu hình key và model trước khi bật AI thật.")
        if self.app_env == "production":
            raise ValueError("Production chưa được mở: cần hoàn thành M7/M8 và go-live gates.")
        if self.embedding_provider != "disabled" and (
            not self.embedding_profile_id or not self.embedding_dimensions
        ):
            raise ValueError("Embedding profile và dimensions phải do Developer cấu hình rõ.")
        if self.embedding_provider == "openai" and (
            not self.openai_embedding_model or not self.openai_api_key.get_secret_value()
        ):
            raise ValueError("Embedding API cần model/key được Developer cấu hình.")
        return self

    @property
    def runtime_fingerprint(self) -> str:
        raw = f"m1-v1:{self.ai_provider}:{self.openai_chat_model}:{self.ai_max_output_tokens}"
        if self.embedding_provider != "disabled":
            raw += f":{self.embedding_fingerprint}"
        return sha256(raw.encode()).hexdigest()

    @property
    def embedding_fingerprint(self) -> str:
        return sha256(
            f"m2-chunker-v1:{self.embedding_provider}:{self.openai_embedding_model}:{self.embedding_dimensions}".encode()
        ).hexdigest()


@lru_cache
def settings() -> Settings:
    return Settings()
