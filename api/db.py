"""Engine e sessão SQLAlchemy async (ADR-006)."""
from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from api.config import obter_configuracao

_engine: AsyncEngine | None = None
_criar_sessao: async_sessionmaker[AsyncSession] | None = None


def obter_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        cfg = obter_configuracao()
        _engine = create_async_engine(
            cfg.url_banco,
            pool_size=5,
            max_overflow=5,
            pool_pre_ping=True,
            echo=False,
        )
    return _engine


def obter_criador_sessao() -> async_sessionmaker[AsyncSession]:
    global _criar_sessao
    if _criar_sessao is None:
        _criar_sessao = async_sessionmaker(
            obter_engine(), expire_on_commit=False, autoflush=False
        )
    return _criar_sessao


async def obter_sessao() -> AsyncIterator[AsyncSession]:
    """Dependência do FastAPI: fecha a sessão ao fim do request."""
    async with obter_criador_sessao()() as sessao:
        yield sessao


async def encerrar_engine() -> None:
    global _engine, _criar_sessao
    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _criar_sessao = None
