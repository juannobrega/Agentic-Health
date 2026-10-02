"""Endpoints de estatísticas e coortes (E3)."""
import csv
import io
from datetime import datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from api.db import obter_sessao
from api.esquemas.comum import FiltroQualidade
from api.esquemas.estatistica import (
    CriteriosCoorte,
    ListaPrevalencia,
    PreviaCoorte,
    ResultadoCoorte,
    ResumoPopulacional,
)
from api.esquemas.paciente import PacienteResumo
from api.repositorios import estatistica as repo

roteador = APIRouter(tags=["estatísticas"])

LIMITE_EXPORTACAO = 1000


@roteador.get(
    "/estatisticas/resumo",
    response_model=ResumoPopulacional,
    summary="Resumo populacional",
    description=(
        "Números-chave da base numa chamada.\n\n"
        "**Não há estatística de valor de exame** — o dataset não traz "
        "resultados (ADR-008)."
    ),
)
async def obter_resumo(
    sessao: Annotated[AsyncSession, Depends(obter_sessao)],
) -> ResumoPopulacional:
    return ResumoPopulacional(**await repo.resumo_populacional(sessao))


@roteador.get(
    "/estatisticas/{dominio}",
    response_model=ListaPrevalencia,
    summary="Prevalência por domínio",
    description=(
        "Distingue **ocorrências** de **pacientes afetados** — confundir os dois "
        "é o erro mais fácil aqui. Exemplo: 'Infecção viral das vias aéreas "
        "superiores' tem 1.134 ocorrências em 711 pacientes; a prevalência é "
        "sobre os 711.\n\n"
        "Domínios: `condicoes` (134), `medicamentos` (145 válidos), "
        "`procedimentos` (91), `exames` (240 — sem resultados)."
    ),
)
async def obter_prevalencia(
    dominio: Literal["condicoes", "medicamentos", "procedimentos", "exames"],
    sessao: Annotated[AsyncSession, Depends(obter_sessao)],
    pagina: Annotated[int, Query(ge=1)] = 1,
    por_pagina: Annotated[int, Query(ge=1, le=200)] = 25,
    sexo: Annotated[Literal["M", "F"] | None, Query()] = None,
    raca: Annotated[str | None, Query()] = None,
    idade_min: Annotated[int | None, Query(ge=0, le=130)] = None,
    idade_max: Annotated[int | None, Query(ge=0, le=130)] = None,
    ordenar_por: Annotated[
        Literal["pacientes", "ocorrencias", "nome"], Query()
    ] = "pacientes",
) -> ListaPrevalencia:
    itens, total, denominador, motivo = await repo.prevalencia(
        sessao,
        dominio,
        pagina=pagina,
        por_pagina=por_pagina,
        sexo=sexo,
        raca=raca,
        idade_min=idade_min,
        idade_max=idade_max,
        ordenar_por=ordenar_por,
    )
    return ListaPrevalencia(
        itens=itens,
        total=total,
        denominador=denominador,
        filtro_qualidade=(
            FiltroQualidade(descricao=motivo) if motivo else None
        ),
    )


async def _validar_criterios(sessao: AsyncSession, criterios: CriteriosCoorte) -> None:
    """Nome inexistente devolve 400 com sugestão, não coorte vazia silenciosa."""
    for campo, dominio in (("condicoes", "condicoes"), ("medicamentos", "medicamentos")):
        pedidos = getattr(criterios, campo)
        if not pedidos:
            continue
        validos = await repo.nomes_validos(sessao, dominio)
        desconhecidos = [p for p in pedidos if p not in validos]
        if desconhecidos:
            exemplos = sorted(validos)[:3]
            raise HTTPException(
                400,
                f"{campo}: valor desconhecido {desconhecidos}. "
                f"Use /busca ou /dicionario para achar o nome exato. "
                f"Exemplos válidos: {exemplos}",
            )


@roteador.post(
    "/coortes/previa",
    response_model=PreviaCoorte,
    summary="Prévia da coorte (só a contagem)",
    description="Para feedback ao vivo enquanto o usuário monta os critérios.",
)
async def previa_coorte(
    criterios: CriteriosCoorte,
    sessao: Annotated[AsyncSession, Depends(obter_sessao)],
) -> PreviaCoorte:
    await _validar_criterios(sessao, criterios)
    total, filtros = await repo.contar_coorte(sessao, criterios)
    return PreviaCoorte(total=total, filtros_aplicados=filtros)


@roteador.post(
    "/coortes",
    response_model=ResultadoCoorte,
    summary="Montar coorte",
    description=(
        "Combina critérios e devolve os pacientes. A resposta declara **todos** "
        "os filtros aplicados, inclusive os de qualidade (ADR-008).\n\n"
        "Combinação sem resultado retorna `total: 0` — não é erro. Critério com "
        "nome inexistente retorna 400, para não parecer coorte vazia."
    ),
)
async def criar_coorte(
    criterios: CriteriosCoorte,
    sessao: Annotated[AsyncSession, Depends(obter_sessao)],
    pagina: Annotated[int, Query(ge=1)] = 1,
    por_pagina: Annotated[int, Query(ge=1, le=100)] = 25,
) -> ResultadoCoorte:
    if (
        criterios.idade_min is not None
        and criterios.idade_max is not None
        and criterios.idade_min > criterios.idade_max
    ):
        raise HTTPException(400, "idade_min não pode ser maior que idade_max")

    await _validar_criterios(sessao, criterios)
    itens, total, filtros = await repo.montar_coorte(
        sessao, criterios, pagina=pagina, por_pagina=por_pagina
    )
    return ResultadoCoorte(
        total=total,
        pagina=pagina,
        por_pagina=por_pagina,
        itens=[PacienteResumo.model_validate(i) for i in itens],
        filtros_aplicados=filtros,
    )


@roteador.post(
    "/coortes/exportar",
    summary="Exportar coorte em CSV",
    description=(
        f"CSV com os critérios no cabeçalho. Limite de {LIMITE_EXPORTACAO} "
        "linhas.\n\n"
        "Inclui o UUID além do `id_pessoa`: o ID é sequencial e específico desta "
        "carga, enquanto o UUID é o identificador estável para cruzar com outra "
        "fonte (ADR-009)."
    ),
    responses={200: {"content": {"text/csv": {}}}},
)
async def exportar_coorte(
    criterios: CriteriosCoorte,
    sessao: Annotated[AsyncSession, Depends(obter_sessao)],
) -> StreamingResponse:
    await _validar_criterios(sessao, criterios)
    total, filtros = await repo.contar_coorte(sessao, criterios)
    if total > LIMITE_EXPORTACAO:
        raise HTTPException(
            400,
            f"Coorte com {total} pacientes excede o limite de "
            f"{LIMITE_EXPORTACAO}. Refine os critérios.",
        )

    itens, _, _ = await repo.montar_coorte(
        sessao, criterios, pagina=1, por_pagina=LIMITE_EXPORTACAO
    )

    buffer = io.StringIO()
    buffer.write("﻿")  # BOM: Excel abre UTF-8 corretamente
    buffer.write(f"# Coorte exportada em {datetime.now():%d/%m/%Y %H:%M}\n")
    buffer.write(f"# Total: {total} pacientes\n")
    for filtro in filtros:
        buffer.write(f"# Filtro: {filtro}\n")
    buffer.write("# Dados sintéticos (Synthea / OMOP CDM)\n")

    escritor = csv.writer(buffer)
    escritor.writerow(
        ["id_pessoa", "codigo_origem_pessoa", "sexo", "idade", "raca", "etnia"]
    )
    for p in itens:
        escritor.writerow(
            [p.id_pessoa, p.codigo_origem_pessoa, p.sexo, p.idade, p.raca, p.etnia]
        )

    buffer.seek(0)
    nome = f"coorte_{datetime.now():%Y%m%d_%H%M%S}.csv"
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{nome}"'},
    )
