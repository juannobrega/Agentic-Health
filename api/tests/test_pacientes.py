"""Testes dos endpoints de paciente (E1)."""
import pytest
from httpx import ASGITransport, AsyncClient

from api.main import app

# paciente com maior volume de eventos: 2.486 exames
ID_MAIOR_VOLUME = 736
# anos de nascimento implausíveis (ADR-008)
ID_NASCIMENTO_INVALIDO = 265


@pytest.fixture
async def cliente():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://teste"
    ) as c:
        yield c


# ------------------------------------------------------------ HU-1.1 lista


@pytest.mark.asyncio
async def test_listar_exclui_nascimentos_implausiveis(cliente):
    """1.128 de 1.130 — os 2 implausíveis ficam fora (ADR-008)."""
    r = await cliente.get("/pacientes")
    assert r.status_code == 200
    assert r.json()["total"] == 1128


@pytest.mark.asyncio
async def test_listar_pagina(cliente):
    r = await cliente.get("/pacientes", params={"por_pagina": 5})
    corpo = r.json()
    assert len(corpo["itens"]) == 5
    assert corpo["por_pagina"] == 5
    assert corpo["pagina"] == 1


@pytest.mark.asyncio
async def test_listar_filtra_por_sexo(cliente):
    r = await cliente.get("/pacientes", params={"sexo": "F", "por_pagina": 100})
    assert all(i["sexo"] == "F" for i in r.json()["itens"])


@pytest.mark.asyncio
async def test_listar_filtra_por_faixa_de_idade(cliente):
    r = await cliente.get(
        "/pacientes", params={"idade_min": 40, "idade_max": 60, "por_pagina": 100}
    )
    assert all(40 <= i["idade"] <= 60 for i in r.json()["itens"])


@pytest.mark.asyncio
async def test_listar_filtra_por_condicao(cliente):
    r = await cliente.get("/pacientes", params={"condicao": "Hipertensão arterial"})
    assert r.json()["total"] == 299


@pytest.mark.asyncio
async def test_listar_rejeita_faixa_de_idade_invertida(cliente):
    r = await cliente.get("/pacientes", params={"idade_min": 60, "idade_max": 40})
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_listar_rejeita_ordenacao_fora_da_allowlist(cliente):
    """Ordenação é mapeada a atributo do modelo, não a string livre (ADR-006)."""
    r = await cliente.get("/pacientes", params={"ordenar_por": "codigo_origem_pessoa"})
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_listar_respeita_limite_de_pagina(cliente):
    r = await cliente.get("/pacientes", params={"por_pagina": 500})
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_listar_ordena_por_idade(cliente):
    r = await cliente.get(
        "/pacientes", params={"ordenar_por": "idade", "decrescente": True, "por_pagina": 10}
    )
    idades = [i["idade"] for i in r.json()["itens"]]
    assert idades == sorted(idades, reverse=True)


# --------------------------------------------------------- HU-1.2 detalhe


@pytest.mark.asyncio
async def test_detalhe_traz_contadores_e_janela(cliente):
    r = await cliente.get(f"/pacientes/{ID_MAIOR_VOLUME}")
    assert r.status_code == 200
    corpo = r.json()
    assert corpo["id_pessoa"] == ID_MAIOR_VOLUME
    assert corpo["codigo_origem_pessoa"]
    assert corpo["contadores"]["exames"] == 2486
    assert corpo["janela_observacao"]["data_inicio"]


@pytest.mark.asyncio
async def test_detalhe_404_para_inexistente(cliente):
    r = await cliente.get("/pacientes/999999")
    assert r.status_code == 404
    assert "não encontrado" in r.json()["detail"]


@pytest.mark.asyncio
async def test_detalhe_avisa_sobre_nascimento_implausivel(cliente):
    """Retorna o dado com aviso, não erro (HU-1.2)."""
    r = await cliente.get(f"/pacientes/{ID_NASCIMENTO_INVALIDO}")
    assert r.status_code == 200
    corpo = r.json()
    assert corpo["idade"] is None
    assert corpo["aviso"] is not None
    assert "implausível" in corpo["aviso"]


# -------------------------------------------------------- HU-1.3 timeline


@pytest.mark.asyncio
async def test_timeline_unifica_os_quatro_dominios(cliente):
    r = await cliente.get(
        f"/pacientes/{ID_MAIOR_VOLUME}/timeline", params={"por_pagina": 100}
    )
    assert r.status_code == 200
    corpo = r.json()
    assert corpo["total"] == 2708
    tipos = {i["tipo"] for i in corpo["itens"]}
    assert tipos <= {"condicao", "medicamento", "procedimento", "exame"}


@pytest.mark.asyncio
async def test_timeline_marca_exames_sem_valor(cliente):
    """ADR-008: a limitação viaja junto com o dado."""
    r = await cliente.get(
        f"/pacientes/{ID_MAIOR_VOLUME}/timeline",
        params={"tipo": "exame", "por_pagina": 20},
    )
    itens = r.json()["itens"]
    assert itens
    assert all(i["valor_disponivel"] is False for i in itens)


@pytest.mark.asyncio
async def test_timeline_filtra_por_tipo(cliente):
    r = await cliente.get(
        f"/pacientes/{ID_MAIOR_VOLUME}/timeline", params={"tipo": "exame"}
    )
    assert r.json()["total"] == 2486


@pytest.mark.asyncio
async def test_timeline_aceita_multiplos_tipos(cliente):
    r = await cliente.get(
        f"/pacientes/{ID_MAIOR_VOLUME}/timeline",
        params=[("tipo", "condicao"), ("tipo", "medicamento")],
    )
    assert r.json()["total"] == 121


@pytest.mark.asyncio
async def test_timeline_ordenada_por_data_decrescente(cliente):
    r = await cliente.get(
        f"/pacientes/{ID_MAIOR_VOLUME}/timeline", params={"por_pagina": 30}
    )
    datas = [i["data"] for i in r.json()["itens"] if i["data"]]
    assert datas == sorted(datas, reverse=True)


@pytest.mark.asyncio
async def test_timeline_filtra_por_periodo(cliente):
    r = await cliente.get(
        f"/pacientes/{ID_MAIOR_VOLUME}/timeline",
        params={"data_de": "1990-01-01", "data_ate": "1990-12-31", "por_pagina": 100},
    )
    for item in r.json()["itens"]:
        assert item["data"].startswith("1990")


@pytest.mark.asyncio
async def test_timeline_404_para_inexistente(cliente):
    r = await cliente.get("/pacientes/999999/timeline")
    assert r.status_code == 404


# ------------------------------------------------- HU-1.4 abas por domínio


@pytest.mark.asyncio
async def test_medicamentos_declaram_o_filtro_de_qualidade(cliente):
    """A resposta informa quantos foram excluídos e por quê (ADR-008)."""
    r = await cliente.get("/pacientes/1/medicamentos")
    assert r.status_code == 200
    corpo = r.json()
    assert corpo["total"] == 8
    assert corpo["filtro_qualidade"]["registros_excluidos"] == 1
    assert "RxNorm" in corpo["filtro_qualidade"]["descricao"]


@pytest.mark.asyncio
async def test_exames_tem_valor_nulo_documentado(cliente):
    r = await cliente.get(f"/pacientes/{ID_MAIOR_VOLUME}/exames")
    corpo = r.json()
    assert corpo["total"] == 2486
    assert all(i["valor_numerico"] is None for i in corpo["itens"])


@pytest.mark.asyncio
async def test_condicoes_e_procedimentos(cliente):
    r = await cliente.get(f"/pacientes/{ID_MAIOR_VOLUME}/condicoes")
    assert r.json()["total"] == 15
    r = await cliente.get(f"/pacientes/{ID_MAIOR_VOLUME}/procedimentos")
    assert r.json()["total"] == 101


# ------------------------------------------------------- HU-1.5 alergias


@pytest.mark.asyncio
async def test_alergias_do_paciente(cliente):
    r = await cliente.get("/pacientes/7/alergias")
    assert r.status_code == 200
    assert any("amendoim" in a["nome_observacao"].lower() for a in r.json())


@pytest.mark.asyncio
async def test_sem_alergia_retorna_lista_vazia(cliente):
    """Lista vazia, não 404 (HU-1.5)."""
    r = await cliente.get(f"/pacientes/{ID_MAIOR_VOLUME}/alergias")
    assert r.status_code == 200
    assert r.json() == []
