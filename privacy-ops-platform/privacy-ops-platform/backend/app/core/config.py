"""
Central application configuration, loaded from environment variables.
Never hard-code secrets here — this module only defines shape and defaults;
actual values come from .env / the deployment's secrets manager.
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "local"
    app_secret_key: str = "dev-only-change-me"
    api_v1_prefix: str = "/api/v1"

    database_url: str = "postgresql+asyncpg://privacy_app:change-me@localhost:5432/privacy_ops"

    redis_url: str = "redis://localhost:6379/0"

    object_storage_endpoint: str = "http://localhost:9000"
    object_storage_access_key: str = "minioadmin"
    object_storage_secret_key: str = "change-me"
    object_storage_bucket: str = "privacy-ops-evidence"
    object_storage_region: str = "us-east-1"

    oidc_issuer: str = ""
    oidc_client_id: str = ""
    oidc_client_secret: str = ""
    oidc_redirect_uri: str = ""

    cors_allowed_origins: str = "http://localhost:3000"

    default_tenant_id: str = "00000000-0000-0000-0000-000000000001"
    default_organization_name: str = "Default Organization"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_allowed_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
