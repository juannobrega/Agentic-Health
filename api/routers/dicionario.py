"""Endpoints de dicionário e busca (E4)."""
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession

from api.db import obter_sessao
from api.esquemas.comum import Pagina
from api.esquemas.estatistica import ItemDicionario, ResultadoBusca, Sugestao
from api.repositorios import estatistica as repo

roteador = APIRouter(tags=["dicionário"])

MIN_TERMO = 2


@roteador.get(
    "/dicionario",
    response_model=Pagina[ItemDicionario],
    summary="Dicionário de conceitos clínicos",
    description=(
        "Os 535 códigos usados no dataset: SNOMED CT (272), RxNorm (146) e "
        "LOINC (117).\n\n"
        "**As traduções não têm fonte auditável**: foram feitas a partir dos "
        "códigos, sem o vocabulário oficial do OHDSI. Para uso clínico, valide "
        "contra o Athena (ADR-001).\n\n"
        "134 códigos trazem `observacao` preenchida, marcando o bug de ETL."
    ),
)
async def listar_dicionario(
    sessao: Annotated[AsyncSession, Depends(obter_sessao)],
    pagina: Annotated[int, Query(ge=1)] = 1,
    por_pagina: Annotated[int, Query(ge=1, le=200)] = 50,
    vocabulario: Annotated[
        Literal["SNOMED CT", "RxNorm", "LOINC"] | None, Query()
    ] = None,
    dominio: Annotated[str | None, Query(description="condição, exame…")] = None,
    q: Annotated[str | None, Query(description="Busca no nome ou no código")] = None,
) -> Pagina[ItemDicionario]:
    itens, total = await repo.listar_dicionario(
        sessao,
        pagina=pagina,
        por_pagina=por_pagina,
        vocabulario=vocabulario,
        dominio=dominio,
        termo=q,
    )
    return Pagina(
        itens=[ItemDicionario.model_validate(i) for i in itens],
        total=total,
        pagina=pagina,
        por_pagina=por_pagina,
    )


@roteador.get(
    "/dicionario/sugestoes",
    response_model=list[Sugestao],
    summary="Autocomplete de nome clínico",
    description="Até 10 sugestões, as mais frequentes primeiro.",
)
async def obter_sugestoes(
    sessao: Annotated[AsyncSession, Depends(obter_sessao)],
    q: Annotated[str, Query(min_length=MIN_TERMO)],
    dominio: Annotated[
        Literal["condicoes", "medicamentos", "procedimentos", "exames", "observacoes"],
        Query(),
    ] = "condicoes",
    limite: Annotated[int, Query(ge=1, le=25)] = 10,
) -> list[Sugestao]:
    return [
        Sugestao(**s) for s in await repo.sugestoes(sessao, dominio, q, limite)
    ]


@roteador.get(
    "/dicionario/{codigo}",
    response_model=ItemDicionario,
    summary="Conceito por código",
)
async def obter_conceito(
    codigo: Annotated[str, Path(description="Código SNOMED, RxNorm ou LOINC")],
    sessao: Annotated[AsyncSession, Depends(obter_sessao)],
) -> ItemDicionario:
    conceito = await repo.obter_conceito(sessao, codigo)
    if conceito is None:
        raise HTTPException(404, f"Código {codigo} não encontrado no dicionário")
    return ItemDicionario.model_validate(conceito)


@roteador.get(
    "/busca",
    response_model=ResultadoBusca,
    tags=["busca"],
    summary="Buscar termo clínico em português",
    description=(
        "Busca nos nomes clínicos de todos os domínios, **ignorando acento e "
        "caixa**: 'pre-diabetes' acha 'Pré-diabetes'.\n\n"
        "O banco usa locale C, então a normalização vem do `unaccent` (ADR-002)."
    ),
)
async def buscar(
    sessao: Annotated[AsyncSession, Depends(obter_sessao)],
    q: Annotated[str, Query(min_length=MIN_TERMO, description="Mínimo 2 caracteres")],
) -> ResultadoBusca:
    resultados, truncado = await repo.buscar(sessao, q)
    return ResultadoBusca(termo=q, truncado=truncado, **resultados)
