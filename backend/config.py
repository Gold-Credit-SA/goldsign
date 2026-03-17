"""Configuracoes do backend via variaveis de ambiente."""

from functools import lru_cache
from urllib.parse import urlparse

from pydantic import model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Supabase
    supabase_url: str | None = None
    supabase_service_key: str | None = None
    supabase_db_url: str | None = None
    supabase_bucket: str = "documentos-pdf"

    # JWT
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    jwt_expiration_minutes: int = 60

    # App
    app_name: str = "Assinatura Digital ICP-Brasil"
    frontend_url: str = "http://localhost:3000"
    backend_url: str = "http://localhost:8000"

    # Assinatura
    signature_field_name: str = "AssinaturaICP"
    signature_reason: str = "Assinatura digital conforme ICP-Brasil"
    signature_location: str = "Brasil"

    # Link
    signing_link_expiration_days: int = 7

    @model_validator(mode="after")
    def validar_supabase(self):
        if not self.supabase_url and self.supabase_db_url:
            parsed = urlparse(self.supabase_db_url)
            host = parsed.hostname or ""
            if host.startswith("db."):
                project_ref = host.removeprefix("db.").split(".")[0]
                self.supabase_url = f"https://{project_ref}.supabase.co"

        if not self.supabase_url:
            raise ValueError(
                "SUPABASE_URL nao configurada. "
                "Defina SUPABASE_URL ou SUPABASE_DB_URL no .env."
            )

        if not self.supabase_service_key:
            raise ValueError(
                "SUPABASE_SERVICE_KEY nao configurada. "
                "Use a service_role key em Settings > API no Supabase."
            )

        return self

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
