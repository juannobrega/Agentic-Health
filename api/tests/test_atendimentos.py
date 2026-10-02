"""Testes de atendimento e trajetória (E2)."""
import pytest
from httpx import ASGITransport, AsyncClient

from api.main import app

ID_MAIOR_VOLUME = 736
ID_ATENDIMENTO_DENSO = 15705  # 97 exames


@pytest.fixture
async def cliente():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://teste"
    ) as c:
        yield c


# ------------------------------------------------------- HU-2.1 listagem


@pytest.mark.asyncio
async def test_listar_atendimentos(cliente):
    r = await cliente.get("/atendimentos")
    assert r.status_code == 200
    assert r.json()["total"] == 32153


@pytest.mark.asyncio
async def test_distribuicao_por_tipo(cliente):
    esperado = {"Ambulatorial": 29343, "Emergência": 1809, "Internação": 1001}
    for tipo, qtd in esperado.items():
        r = await cliente.get("/atendimentos", params={"tipo": tipo})
        assert r.json()["total"] == qtd, tipo


@pytest.mark.asyncio
async def test_tipo_invalido_rejeitado(cliente):
    r = await cliente.get("/atendimentos", params={"tipo": "Teleconsulta"})
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_filtra_por_paciente(cliente):
    r = await cliente.get("/atendimentos", params={"id_pessoa": ID_MAIOR_VOLUME})
    corpo = r.json()
    assert corpo["total"] == 66
    assert all(i["id_pessoa"] == ID_MAIOR_VOLUME for i in corpo["itens"])


@pytest.mark.asyncio
async def test_duracao_calculada(cliente):
    r = await cliente.get("/atendimentos", params={"por_pagina": 20})
    for item in r.json()["itens"]:
        if item["data_inicio"] and item["data_fim"]:
            assert item["duracao_dias"] is not None
            assert item["duracao_dias"] >= 0


@pytest.mark.asyncio
async def test_rejeita_periodo_invertido(cliente):
    r = await cliente.get(
        "/atendimentos", params={"data_de": "2019-01-01", "data_ate": "2010-01-01"}
    )
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_ordenacao_decrescente_por_padrao(cliente):
    r = await cliente.get("/atendimentos", params={"por_pagina": 15})
    datas = [i["data_inicio"] for i in r.json()["itens"] if i["data_inicio"]]
    assert datas == sorted(datas, reverse=True)


# -------------------------------------------------------- HU-2.2 detalhe


@pytest.mark.asyncio
async def test_detalhe_traz_todos_os_dominios(cliente):
    r = await cliente.get(f"/atendimentos/{ID_ATENDIMENTO_DENSO}")
    assert r.status_code == 200
    corpo = r.json()
    assert len(corpo["exames"]) == 97
    assert len(corpo["condicoes"]) == 3
    assert len(corpo["procedimentos"]) == 3
    assert len(corpo["medicamentos"]) == 4


@pytest.mark.asyncio
async def test_detalhe_marca_exames_sem_valor(cliente):
    """ADR-008 também no detalhe do atendimento."""
    r = await cliente.get(f"/atendimentos/{ID_ATENDIMENTO_DENSO}")
    assert all(e["valor_numerico"] is None for e in r.json()["exames"])


@pytest.mark.asyncio
async def test_detalhe_404(cliente):
    r = await cliente.get("/atendimentos/9999999")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_secao_vazia_vem_como_lista(cliente):
    """Lista vazia, não campo omitido (HU-2.2)."""
    r = await cliente.get("/atendimentos", params={"por_pagina": 1})
    id_qualquer = r.json()["itens"][0]["id_atendimento"]
    corpo = (await cliente.get(f"/atendimentos/{id_qualquer}")).json()
    for chave in ("condicoes", "medicamentos", "procedimentos", "exames"):
        assert isinstance(corpo[chave], list)


# ----------------------------------------------------- HU-2.3 trajetória


@pytest.mark.asyncio
async def test_trajetoria_segue_o_encadeamento(cliente):
    r = await cliente.get(f"/pacientes/{ID_MAIOR_VOLUME}/trajetoria")
    assert r.status_code == 200
    corpo = r.json()
    assert corpo["total_atendimentos"] == 66
    assert corpo["ciclo_detectado"] is False
    assert corpo["truncada"] is False


@pytest.mark.asyncio
async def test_trajetoria_ordenada_e_com_intervalo(cliente):
    r = await cliente.get(f"/pacientes/{ID_MAIOR_VOLUME}/trajetoria")
    passos = r.json()["passos"]
    assert [p["ordem"] for p in passos] == list(range(1, len(passos) + 1))
    # o primeiro passo não tem anterior
    assert passos[0]["dias_desde_anterior"] is None
    assert any(p["dias_desde_anterior"] is not None for p in passos[1:])


@pytest.mark.asyncio
async def test_trajetoria_traz_condicoes_do_passo(cliente):
    r = await cliente.get("/pacientes/1/trajetoria")
    passos = r.json()["passos"]
    assert any(p["condicoes"] for p in passos)


@pytest.mark.asyncio
async def test_trajetoria_404(cliente):
    r = await cliente.get("/pacientes/999999/trajetoria")
    assert r.status_code == 404


# --------------------------------------------------- HU-2.4 reinternações


@pytest.mark.asyncio
async def test_reinternacoes_lista_os_78(cliente):
    r = await cliente.get("/estatisticas/reinternacoes")
    assert r.status_code == 200
    assert r.json()["total"] == 78


@pytest.mark.asyncio
async def test_reinternacoes_ordenadas_por_frequencia(cliente):
    r = await cliente.get("/estatisticas/reinternacoes", params={"por_pagina": 10})
    internacoes = [i["internacoes"] for i in r.json()["itens"]]
    assert internacoes == sorted(internacoes, reverse=True)
    assert all(n > 1 for n in internacoes)


@pytest.mark.asyncio
async def test_reinternacoes_filtra_por_janela(cliente):
    r = await cliente.get("/estatisticas/reinternacoes", params={"janela_dias": 30})
    corpo = r.json()
    assert corpo["total"] == 11
    assert all(i["menor_intervalo_dias"] <= 30 for i in corpo["itens"])


@pytest.mark.asyncio
async def test_reinternacao_documenta_que_nao_e_readmissao_clinica(cliente):
    """A descrição precisa impedir leitura como indicador de qualidade."""
    r = await cliente.get("/openapi.json")
    descricao = r.json()["paths"]["/estatisticas/reinternacoes"]["get"]["description"]
    assert "não" in descricao and "readmissão" in descricao
