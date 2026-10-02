"""Fixtures de teste.

O engine global de api/db.py é cacheado em módulo e fica atrelado ao event loop
que o criou. Como o pytest-asyncio abre um loop por teste, reusá-lo produz
"attached to a different loop". Aqui criamos um engine próprio por teste.
"""
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from api.config import obter_configuracao
from api.db import descartar_engine_sem_fechar


@pytest_asyncio.fixture(autouse=True)
async def _engine_isolado():
    """Garante que cada teste comece e termine sem engine global cacheado."""
    descartar_engine_sem_fechar()
    yield
    descartar_engine_sem_fechar()


@pytest_asyncio.fixture
async def sessao() -> AsyncSession:
    cfg = obter_configuracao()
    # NullPool: sem conexão sobrevivendo ao loop do teste
    engine = create_async_engine(cfg.url_banco, poolclass=NullPool)
    try:
        criar = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
        async with criar() as s:
            yield s
    finally:
        await engine.dispose()
