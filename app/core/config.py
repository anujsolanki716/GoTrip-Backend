from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

DEV_SECRET = "dev-only-insecure-secret-change-me-0123456789"  


def _split_csv(value: object) -> object:
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    return value


CsvList = Annotated[list[str], NoDecode]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    environment: Literal["development", "test", "production"] = "development"
    app_name: str = "GoTrip API"
    api_prefix: str = "/api/v1"
    log_level: str = "INFO"

    database_url: str = "postgresql+psycopg://asolanki:gotrip@localhost:5432/gotrip"

    secret_key: SecretStr = SecretStr(DEV_SECRET)
    access_token_expire_minutes: int = 480
    auth_cookie_name: str = "gotrip_admin"
    cookie_secure: bool = False
    cookie_samesite: Literal["lax", "strict", "none"] = "lax"
    cookie_domain: str | None = None
    cors_origins: CsvList = Field(default_factory=lambda: ["http://0.0.0.0:5173"])
    trusted_proxy_count: int = 0

    login_max_attempts: int = 5
    login_window_seconds: int = 900
    enquiry_rate_limit_count: int = 5
    enquiry_rate_limit_window_seconds: int = 600

    business_name: str = "GoTrip"
    business_tagline: str = "Your Journey, Your Rules."
    business_phone: str = "+91 90000 00000"
    business_whatsapp: str = "919000000000"
    business_email: str = "gotrip2626@gmail.com"
    business_address: str = "Greater Noida, Uttar Pradesh, India"
    business_hours: str = "9:00 AM - 9:00 PM, all days"
    service_areas: CsvList = Field(
        default_factory=lambda: [
            "Greater Noida",
            "Greater Noida West",
            "Knowledge Park",
            "Pari Chowk",
            "Noida (selected sectors)",
            "Delhi NCR (on request)",
        ]
    )

    email_provider: Literal["console", "smtp", "resend", "disabled"] = "console"
    email_from: str = "GoTrip <no-reply@gotrip.example>"
    enquiry_notification_to: CsvList = Field(
        default_factory=lambda: ["gotrip2626@gmail.com"]
    )
    send_customer_acknowledgement: bool = True
    smtp_host: str = "localhost"
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: SecretStr | None = None
    smtp_starttls: bool = True
    smtp_use_ssl: bool = False
    resend_api_key: SecretStr | None = None

    storage_backend: Literal["local", "s3"] = "local"
    local_storage_path: Path = Path("./storage")
    s3_bucket: str | None = None
    s3_region: str | None = None
    s3_endpoint_url: str | None = None
    s3_access_key_id: str | None = None
    s3_secret_access_key: SecretStr | None = None
    s3_presign_expiry_seconds: int = 3600
    max_upload_mb: int = 8
    max_images_per_car: int = 12

    _split = field_validator(
        "cors_origins", "service_areas", "enquiry_notification_to", mode="before"
    )(_split_csv)

    @model_validator(mode="after")
    def _check_production(self) -> "Settings":
        if self.environment == "production":
            secret = self.secret_key.get_secret_value()
            if secret == DEV_SECRET or len(secret) < 32:
                raise ValueError(
                    "SECRET_KEY must be set to a random value of at least 32 characters in production"
                )
            if not self.cookie_secure:
                raise ValueError("COOKIE_SECURE must be true in production")
            if self.storage_backend == "s3" and not self.s3_bucket:
                raise ValueError("S3_BUCKET is required when STORAGE_BACKEND=s3")
        return self

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
