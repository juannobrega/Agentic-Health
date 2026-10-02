"""Testes dos endpoints de saúde (HU-5.1, HU-5.6)."""
import pytest
from httpx import ASGITransport, AsyncClient

from api.main import app


@pytest.fixture
async def cliente():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://teste"
    ) as c:
        yield c


@pytest.mark.asyncio
async def test_raiz(cliente):
    r = await cliente.get("/")
    assert r.status_code == 200
    assert r.json()["api"] == "Agentic Health"


@pytest.mark.asyncio
async def test_saude(cliente):
    r = await cliente.get("/saude")
    assert r.status_code == 200
    corpo = r.json()
    assert corpo["status"] == "ok"
    assert corpo["banco_conectado"] is True


@pytest.mark.asyncio
async def test_saude_dados_confere_as_11_tabelas(cliente):
    r = await cliente.get("/saude/dados")
    assert r.status_code == 200
    corpo = r.json()
    assert corpo["carregado"] is True
    assert corpo["conforme"] is True, corpo["resumo"]
    assert len(corpo["tabelas"]) == 11
    assert all(t["conforme"] for t in corpo["tabelas"])


@pytest.mark.asyncio
async def test_openapi_documenta_as_limitacoes(cliente):
    """A descrição da API precisa carregar as ressalvas (ADR-008)."""
    r = await cliente.get("/openapi.json")
    assert r.status_code == 200
    descricao = r.json()["info"]["description"]
    assert "valor_numerico" in descricao
    assert "7.899" in descricao
    assert "autenticação" in descricao.lower()
