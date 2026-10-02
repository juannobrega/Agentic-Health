"""Configuração da API, lida do .env único na raiz do projeto (ADR-003)."""
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# api/ -> raiz do projeto
RAIZ_PROJETO = Path(__file__).resolve().parent.parent


class Configuracao(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=RAIZ_PROJETO / ".env",
        extra="ignore",
    )

    postgres_db: str = "agentic_health"
    postgres_user: str = "postgres"
    postgres_password: str = "postgres"
    postgres_host: str = "localhost"
    postgres_port: int = 5432

    # schema onde o dataset foi carregado (ADR-002)
    schema_dados: str = "synthea"

    # origens liberadas no CORS. Sem autenticação (ADR-005), restringir a origem
    # é o que evita que qualquer página consuma a API pelo navegador do usuário.
    cors_origens: str = "http://localhost:5173,http://localhost:3000"

    @property
    def url_banco(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def url_banco_sincrona(self) -> str:
        """Alembic roda em modo síncrono."""
        return (
            f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def lista_cors_origens(self) -> list[str]:
        return [o.strip() for o in self.cors_origens.split(",") if o.strip()]


@lru_cache
def obter_configuracao() -> Configuracao:
    return Configuracao()
