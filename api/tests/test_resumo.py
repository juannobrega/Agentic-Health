"""Testes do resumo clínico (HU-1.6)."""
import pytest
from httpx import ASGITransport, AsyncClient

from api.main import app

ID_COM_ALERGIA = 7
ID_MAIOR_VOLUME = 736
ID_NASCIMENTO_INVALIDO = 265


@pytest.fixture
async def cliente():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://teste"
    ) as c:
        yield c


@pytest.mark.asyncio
async def test_resumo_retorna_texto(cliente):
    r = await cliente.get(f"/pacientes/{ID_MAIOR_VOLUME}/resumo")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/plain")
    assert f"PACIENTE #{ID_MAIOR_VOLUME}" in r.text


@pytest.mark.asyncio
async def test_resumo_e_deterministico(cliente):
    """Mesma entrada, mesma saída — não há LLM no caminho (HU-1.6)."""
    a = await cliente.get(f"/pacientes/{ID_MAIOR_VOLUME}/resumo")
    b = await cliente.get(f"/pacientes/{ID_MAIOR_VOLUME}/resumo")
    assert a.text == b.text


@pytest.mark.asyncio
async def test_resumo_declara_que_exames_nao_tem_resultado(cliente):
    """A omissão levaria a concluir ausência de alteração (ADR-008)."""
    r = await cliente.get(f"/pacientes/{ID_MAIOR_VOLUME}/resumo")
    assert "não traz resultados" in r.text
    assert "ausência de valores não significa ausência de alteração" in r.text


@pytest.mark.asyncio
async def test_resumo_cobre_todas_as_secoes(cliente):
    r = await cliente.get(f"/pacientes/{ID_MAIOR_VOLUME}/resumo")
    for secao in (
        "ALERGIAS",
        "CONDIÇÕES",
        "MEDICAMENTOS",
        "ATENDIMENTOS",
        "PROCEDIMENTOS",
        "EXAMES",
    ):
        assert secao in r.text, f"seção ausente: {secao}"


@pytest.mark.asyncio
async def test_resumo_lista_alergia_quando_existe(cliente):
    r = await cliente.get(f"/pacientes/{ID_COM_ALERGIA}/resumo")
    assert "amendoim" in r.text.lower()


@pytest.mark.asyncio
async def test_resumo_diz_quando_nao_ha_alergia(cliente):
    """Silêncio sobre alergia é ambíguo; o texto afirma a ausência."""
    r = await cliente.get(f"/pacientes/{ID_MAIOR_VOLUME}/resumo")
    assert "Nenhuma alergia registrada" in r.text


@pytest.mark.asyncio
async def test_resumo_avisa_nascimento_implausivel(cliente):
    r = await cliente.get(f"/pacientes/{ID_NASCIMENTO_INVALIDO}/resumo")
    assert r.status_code == 200
    assert "implausível" in r.text


@pytest.mark.asyncio
async def test_resumo_marca_origem_sintetica(cliente):
    """Evita que o texto copiado para outro sistema pareça dado real."""
    r = await cliente.get(f"/pacientes/{ID_MAIOR_VOLUME}/resumo")
    assert "sintéticos" in r.text
    assert "determinístico" in r.text


@pytest.mark.asyncio
async def test_resumo_404(cliente):
    r = await cliente.get("/pacientes/999999/resumo")
    assert r.status_code == 404
