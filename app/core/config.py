from functools import lru_cache
from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    app_name: str = "Supervisory Findings and Directives Tracking API"
    environment: str = "development"
    database_url: str = "sqlite:///./supervisory.db"
    secret_key: str = Field(default="development-only-change-this-secret-key")
    access_token_minutes: int = 60
    allowed_origins: str = "http://localhost:5173"
    upload_dir: Path = Path("./uploads")
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_from: str = "noreply@example.org"
    smtp_use_tls: bool = True
    alert_scan_seconds: int = 300
    alert_days_before: int = 7
    max_upload_bytes: int = 10 * 1024 * 1024
    minio_endpoint: str = "minio:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket: str = "supervisory-uploads"
    minio_secure: bool = False
    bootstrap_admin_email: str | None = None
    bootstrap_admin_password: str | None = None
    bootstrap_admin_name: str = "System Administrator"

    @property
    def cors_origins(self) -> list[str]:
        return [item.strip() for item in self.allowed_origins.split(",") if item.strip()]

    @property
    def smtp_enabled(self) -> bool:
        return bool(self.smtp_host and self.smtp_from)


@lru_cache
def get_settings() -> Settings:
    return Settings()
