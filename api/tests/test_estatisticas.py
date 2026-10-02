"""Testes de estatísticas, coortes, dicionário e busca (E3, E4)."""
import pytest
from httpx import ASGITransport, AsyncClient

from api.main import app


@pytest.fixture
async def cliente():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://teste"
    ) as c:
        yield c


# ------------------------------------------------------- HU-3.1 resumo


@pytest.mark.asyncio
async def test_resumo_populacional(cliente):
    r = await cliente.get("/estatisticas/resumo")
    assert r.status_code == 200
    corpo = r.json()
    assert corpo["total_pacientes"] == 1128
    assert corpo["pacientes_multimorbidade"] == 247
    assert sum(f["pacientes"] for f in corpo["piramide_etaria"]) == 1128


@pytest.mark.asyncio
async def test_resumo_declara_vies_da_populacao(cliente):
    """Raça 75% branca: a UI precisa do aviso (ADR-008)."""
    r = await cliente.get("/estatisticas/resumo")
    corpo = r.json()
    assert "equidade" in corpo["aviso_representatividade"]
    assert "1909" in corpo["janela_temporal"]


@pytest.mark.asyncio
async def test_resumo_atendimentos_por_tipo(cliente):
    r = await cliente.get("/estatisticas/resumo")
    tipos = {t["rotulo"]: t["pacientes"] for t in r.json()["atendimentos_por_tipo"]}
    assert tipos == {"Ambulatorial": 29343, "Emergência": 1809, "Internação": 1001}


# -------------------------------------------------- HU-3.2/3.5 prevalência


@pytest.mark.asyncio
async def test_prevalencia_distingue_ocorrencias_de_pacientes(cliente):
    """1.134 ocorrências em 711 pacientes — não são a mesma coisa."""
    r = await cliente.get("/estatisticas/condicoes", params={"por_pagina": 1})
    corpo = r.json()
    assert corpo["total"] == 134
    assert corpo["denominador"] == 1128
    topo = corpo["itens"][0]
    assert topo["ocorrencias"] == 1134
    assert topo["pacientes"] == 711
    assert topo["ocorrencias"] > topo["pacientes"]


@pytest.mark.asyncio
async def test_prevalencia_percentual_sobre_pacientes(cliente):
    r = await cliente.get("/estatisticas/condicoes", params={"por_pagina": 5})
    corpo = r.json()
    for item in corpo["itens"]:
        esperado = round(100 * item["pacientes"] / corpo["denominador"], 2)
        assert item["percentual_pacientes"] == esperado


@pytest.mark.asyncio
async def test_prevalencia_por_dominio(cliente):
    esperado = {"condicoes": 134, "medicamentos": 145, "procedimentos": 91, "exames": 240}
    for dominio, qtd in esperado.items():
        r = await cliente.get(f"/estatisticas/{dominio}", params={"por_pagina": 1})
        assert r.json()["total"] == qtd, dominio


@pytest.mark.asyncio
async def test_prevalencia_medicamentos_declara_filtro(cliente):
    r = await cliente.get("/estatisticas/medicamentos", params={"por_pagina": 1})
    corpo = r.json()
    assert corpo["filtro_qualidade"] is not None
    assert "7.899" in corpo["filtro_qualidade"]["descricao"]
    # sem o filtro, o topo seria um diagnóstico
    assert "Infecção" not in corpo["itens"][0]["nome"]


@pytest.mark.asyncio
async def test_prevalencia_exames_avisa_sem_resultado(cliente):
    r = await cliente.get("/estatisticas/exames", params={"por_pagina": 1})
    assert "sem resultado" in r.json()["filtro_qualidade"]["descricao"]


@pytest.mark.asyncio
async def test_prevalencia_corte_demografico_reduz_denominador(cliente):
    completo = (await cliente.get("/estatisticas/condicoes")).json()
    cortado = (
        await cliente.get("/estatisticas/condicoes", params={"sexo": "F", "idade_min": 60})
    ).json()
    assert cortado["denominador"] < completo["denominador"]


@pytest.mark.asyncio
async def test_dominio_invalido_rejeitado(cliente):
    r = await cliente.get("/estatisticas/inventado")
    assert r.status_code == 422


# -------------------------------------------------------- HU-3.3 coortes


@pytest.mark.asyncio
async def test_coorte_por_condicao(cliente):
    r = await cliente.post("/coortes", json={"condicoes": ["Hipertensão arterial"]})
    assert r.status_code == 200
    assert r.json()["total"] == 299


@pytest.mark.asyncio
async def test_coorte_e_versus_ou(cliente):
    """condicoes_todas muda a semântica: interseção vs união."""
    duas = ["Hipertensão arterial", "Diabetes mellitus tipo 2"]
    qualquer = (await cliente.post("/coortes", json={"condicoes": duas})).json()
    todas = (
        await cliente.post("/coortes", json={"condicoes": duas, "condicoes_todas": True})
    ).json()
    assert todas["total"] == 46
    assert qualquer["total"] == 322
    assert todas["total"] < qualquer["total"]


@pytest.mark.asyncio
async def test_coorte_combina_criterios(cliente):
    r = await cliente.post(
        "/coortes",
        json={"condicoes": ["Hipertensão arterial"], "sexo": "F", "idade_min": 50},
    )
    corpo = r.json()
    assert corpo["total"] == 95
    assert all(i["sexo"] == "F" and i["idade"] >= 50 for i in corpo["itens"])


@pytest.mark.asyncio
async def test_coorte_declara_filtros_de_qualidade(cliente):
    """Os filtros aplicados vêm na resposta, não escondidos (ADR-008)."""
    r = await cliente.post("/coortes", json={"sexo": "M"})
    filtros = r.json()["filtros_aplicados"]
    assert any("[qualidade]" in f for f in filtros)
    assert any("implausível" in f for f in filtros)


@pytest.mark.asyncio
async def test_coorte_vazia_nao_e_erro(cliente):
    r = await cliente.post(
        "/coortes", json={"condicoes": ["Hipertensão arterial"], "idade_max": 1}
    )
    assert r.status_code == 200
    assert r.json()["total"] == 0


@pytest.mark.asyncio
async def test_coorte_rejeita_nome_inexistente(cliente):
    """400 com sugestão, não coorte vazia silenciosa (HU-3.3)."""
    r = await cliente.post("/coortes", json={"condicoes": ["Hipertensao"]})
    assert r.status_code == 400
    assert "desconhecido" in r.json()["detail"]


@pytest.mark.asyncio
async def test_coorte_rejeita_idade_invertida(cliente):
    r = await cliente.post("/coortes", json={"idade_min": 60, "idade_max": 30})
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_previa_so_devolve_contagem(cliente):
    r = await cliente.post("/coortes/previa", json={"condicoes": ["Asma"]})
    assert r.status_code == 200
    corpo = r.json()
    assert "total" in corpo and "itens" not in corpo
    assert corpo["filtros_aplicados"]


# ------------------------------------------------------ HU-3.4 exportação


@pytest.mark.asyncio
async def test_exportar_csv_com_criterios_no_cabecalho(cliente):
    r = await cliente.post("/coortes/exportar", json={"condicoes": ["Asma"]})
    assert r.status_code == 200
    assert "text/csv" in r.headers["content-type"]
    assert "attachment" in r.headers["content-disposition"]
    texto = r.text
    assert "# Filtro:" in texto
    assert "sintéticos" in texto
    # UUID incluído: o id_pessoa é específico desta carga (ADR-009)
    assert "codigo_origem_pessoa" in texto


@pytest.mark.asyncio
async def test_exportar_rejeita_coorte_grande(cliente):
    r = await cliente.post("/coortes/exportar", json={})
    assert r.status_code == 400
    assert "excede o limite" in r.json()["detail"]


# ------------------------------------------------------ HU-4.1 dicionário


@pytest.mark.asyncio
async def test_dicionario_lista_535_codigos(cliente):
    r = await cliente.get("/dicionario", params={"por_pagina": 1})
    assert r.json()["total"] == 535


@pytest.mark.asyncio
async def test_dicionario_filtra_por_vocabulario(cliente):
    esperado = {"SNOMED CT": 272, "RxNorm": 146, "LOINC": 117}
    for vocab, qtd in esperado.items():
        r = await cliente.get("/dicionario", params={"vocabulario": vocab, "por_pagina": 1})
        assert r.json()["total"] == qtd, vocab


@pytest.mark.asyncio
async def test_dicionario_marca_bug_de_etl(cliente):
    r = await cliente.get("/dicionario", params={"por_pagina": 200})
    com_observacao = [i for i in r.json()["itens"] if i["observacao"]]
    assert com_observacao
    assert any("bug" in i["observacao"].lower() for i in com_observacao)


@pytest.mark.asyncio
async def test_dicionario_por_codigo(cliente):
    r = await cliente.get("/dicionario/8480-6")
    assert r.status_code == 200
    corpo = r.json()
    assert corpo["vocabulario"] == "LOINC"
    assert "sistólica" in corpo["nome_portugues"].lower()


@pytest.mark.asyncio
async def test_dicionario_404(cliente):
    r = await cliente.get("/dicionario/codigo-inexistente")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_dicionario_documenta_falta_de_fonte_auditavel(cliente):
    r = await cliente.get("/openapi.json")
    descricao = r.json()["paths"]["/dicionario"]["get"]["description"]
    assert "auditável" in descricao


# ----------------------------------------------------------- HU-4.2 busca


@pytest.mark.asyncio
async def test_busca_ignora_acento(cliente):
    """'pre-diabetes' precisa achar 'Pré-diabetes' (ADR-002)."""
    r = await cliente.get("/busca", params={"q": "pre-diabetes"})
    assert r.status_code == 200
    assert any("Pré-diabetes" in c for c in r.json()["condicoes"])


@pytest.mark.asyncio
async def test_busca_ignora_cedilha_e_caixa(cliente):
    r = await cliente.get("/busca", params={"q": "INFECCAO"})
    assert r.json()["condicoes"]


@pytest.mark.asyncio
async def test_busca_agrupa_por_dominio(cliente):
    r = await cliente.get("/busca", params={"q": "diabet"})
    corpo = r.json()
    for chave in ("condicoes", "medicamentos", "procedimentos", "exames", "observacoes"):
        assert chave in corpo
    assert len(corpo["condicoes"]) == 12


@pytest.mark.asyncio
async def test_busca_exige_minimo_de_caracteres(cliente):
    r = await cliente.get("/busca", params={"q": "a"})
    assert r.status_code == 422


# ------------------------------------------------------ HU-4.3 autocomplete


@pytest.mark.asyncio
async def test_sugestoes_ordenadas_por_frequencia(cliente):
    r = await cliente.get("/dicionario/sugestoes", params={"q": "hipert"})
    assert r.status_code == 200
    sugestoes = r.json()
    assert sugestoes[0]["nome"] == "Hipertensão arterial"
    ocorrencias = [s["ocorrencias"] for s in sugestoes]
    assert ocorrencias == sorted(ocorrencias, reverse=True)


@pytest.mark.asyncio
async def test_sugestoes_por_dominio(cliente):
    r = await cliente.get(
        "/dicionario/sugestoes", params={"q": "aceta", "dominio": "medicamentos"}
    )
    assert any("Acetaminofeno" in s["nome"] for s in r.json())


@pytest.mark.asyncio
async def test_sugestoes_respeita_limite(cliente):
    r = await cliente.get("/dicionario/sugestoes", params={"q": "a", "limite": 5})
    assert r.status_code == 422  # q tem mínimo de 2
    r = await cliente.get("/dicionario/sugestoes", params={"q": "ab", "limite": 5})
    assert len(r.json()) <= 5
