"""Endpoints de atendimento e trajetória (E2)."""
from datetime import date
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession

from api.db import obter_sessao
from api.esquemas.atendimento import (
    AtendimentoDetalhe,
    AtendimentoResumo,
    ItemReinternacao,
    PassoTrajetoria,
    Trajetoria,
)
from api.esquemas.comum import Pagina
from api.esquemas.paciente import (
    ItemCondicao,
    ItemExame,
    ItemMedicamento,
    ItemProcedimento,
)
from api.repositorios import atendimento as repo
from api.repositorios import paciente as repo_paciente

roteador = APIRouter(tags=["atendimentos"])

TipoAtendimento = Literal["Ambulatorial", "Emergência", "Internação"]


def _duracao(inicio: date | None, fim: date | None) -> int | None:
    return (fim - inicio).days if inicio and fim else None


def _resumo(atendimento) -> AtendimentoResumo:
    return AtendimentoResumo(
        id_atendimento=atendimento.id_atendimento,
        id_pessoa=atendimento.id_pessoa,
        tipo=atendimento.atendimento_descricao,
        data_inicio=atendimento.data_inicio,
        data_fim=atendimento.data_fim,
        duracao_dias=_duracao(atendimento.data_inicio, atendimento.data_fim),
    )


@roteador.get(
    "/atendimentos",
    response_model=Pagina[AtendimentoResumo],
    summary="Listar atendimentos",
    description=(
        "Lista paginada com filtros. A base cobre **1909 a janeiro de 2019** — "
        "um filtro de data baseado em recência retornaria vazio."
    ),
)
async def listar_atendimentos(
    sessao: Annotated[AsyncSession, Depends(obter_sessao)],
    pagina: Annotated[int, Query(ge=1)] = 1,
    por_pagina: Annotated[int, Query(ge=1, le=100)] = 25,
    tipo: Annotated[TipoAtendimento | None, Query()] = None,
    id_pessoa: Annotated[int | None, Query(ge=1)] = None,
    data_de: Annotated[date | None, Query()] = None,
    data_ate: Annotated[date | None, Query()] = None,
    decrescente: Annotated[bool, Query(description="Mais recentes primeiro")] = True,
) -> Pagina[AtendimentoResumo]:
    if data_de and data_ate and data_de > data_ate:
        raise HTTPException(400, "data_de não pode ser posterior a data_ate")

    itens, total = await repo.listar(
        sessao,
        pagina=pagina,
        por_pagina=por_pagina,
        tipo=tipo,
        id_pessoa=id_pessoa,
        data_de=data_de,
        data_ate=data_ate,
        decrescente=decrescente,
    )
    return Pagina(
        itens=[_resumo(a) for a in itens],
        total=total,
        pagina=pagina,
        por_pagina=por_pagina,
    )


@roteador.get(
    "/atendimentos/{id_atendimento}",
    response_model=AtendimentoDetalhe,
    summary="Detalhe do atendimento",
    description=(
        "O atendimento e tudo que aconteceu nele. Seções vazias vêm como lista "
        "vazia, não omitidas.\n\n"
        "Um atendimento chega a 97 exames: a UI deve colapsar seções longas."
    ),
)
async def obter_atendimento(
    id_atendimento: Annotated[int, Path(ge=1)],
    sessao: Annotated[AsyncSession, Depends(obter_sessao)],
) -> AtendimentoDetalhe:
    atendimento = await repo.obter(sessao, id_atendimento)
    if atendimento is None:
        raise HTTPException(404, f"Atendimento {id_atendimento} não encontrado")

    eventos = await repo.eventos_do_atendimento(sessao, id_atendimento)
    pessoa = await repo_paciente.obter(sessao, atendimento.id_pessoa)
    idade = await repo_paciente.obter_idade(sessao, atendimento.id_pessoa)

    return AtendimentoDetalhe(
        **_resumo(atendimento).model_dump(),
        sexo=pessoa.sexo if pessoa else None,
        idade=idade,
        id_atendimento_anterior=atendimento.id_atendimento_anterior,
        condicoes=[ItemCondicao.model_validate(c) for c in eventos["condicoes"]],
        medicamentos=[ItemMedicamento.model_validate(m) for m in eventos["medicamentos"]],
        procedimentos=[
            ItemProcedimento.model_validate(p) for p in eventos["procedimentos"]
        ],
        exames=[ItemExame.model_validate(e) for e in eventos["exames"]],
    )


@roteador.get(
    "/pacientes/{id_pessoa}/trajetoria",
    response_model=Trajetoria,
    tags=["pacientes"],
    summary="Trajetória de atendimentos",
    description=(
        "Sequência de atendimentos seguindo `id_atendimento_anterior` — 31.027 "
        "atendimentos têm predecessor.\n\n"
        "Paciente sem encadeamento recebe os atendimentos em ordem cronológica. "
        "A resposta sinaliza truncamento e detecção de ciclo: nada no dataset "
        "garante que a cadeia seja acíclica."
    ),
)
async def obter_trajetoria(
    id_pessoa: Annotated[int, Path(ge=1)],
    sessao: Annotated[AsyncSession, Depends(obter_sessao)],
) -> Trajetoria:
    if await repo_paciente.obter(sessao, id_pessoa) is None:
        raise HTTPException(404, f"Paciente {id_pessoa} não encontrado")

    linhas, truncada, ciclo = await repo.trajetoria(sessao, id_pessoa)

    # uma query para todas as condições, em vez de uma por passo
    condicoes = await repo.condicoes_por_atendimento(
        sessao, [l["id_atendimento"] for l in linhas]
    )

    passos: list[PassoTrajetoria] = []
    data_anterior: date | None = None
    for linha in linhas:
        data_atual = linha["data_inicio"]
        dias = (
            (data_atual - data_anterior).days
            if data_atual and data_anterior
            else None
        )
        passos.append(
            PassoTrajetoria(
                ordem=linha["ordem"],
                id_atendimento=linha["id_atendimento"],
                tipo=linha["tipo"],
                data_inicio=data_atual,
                dias_desde_anterior=dias,
                condicoes=condicoes.get(linha["id_atendimento"], []),
            )
        )
        data_anterior = data_atual or data_anterior

    return Trajetoria(
        id_pessoa=id_pessoa,
        total_atendimentos=len(passos),
        passos=passos,
        truncada=truncada,
        ciclo_detectado=ciclo,
    )


@roteador.get(
    "/estatisticas/reinternacoes",
    response_model=Pagina[ItemReinternacao],
    tags=["estatísticas"],
    summary="Pacientes com internações repetidas",
    description=(
        "Os 78 pacientes com mais de uma internação no histórico.\n\n"
        "**Atenção:** isto é simplesmente mais de uma internação registrada — "
        "**não** é a definição clínica de readmissão em 30 dias, e não deve ser "
        "lido como indicador de qualidade assistencial."
    ),
)
async def listar_reinternacoes(
    sessao: Annotated[AsyncSession, Depends(obter_sessao)],
    pagina: Annotated[int, Query(ge=1)] = 1,
    por_pagina: Annotated[int, Query(ge=1, le=100)] = 25,
    janela_dias: Annotated[
        int | None,
        Query(ge=1, description="Só pacientes cujo menor intervalo é <= este valor"),
    ] = None,
) -> Pagina[ItemReinternacao]:
    itens, total = await repo.reinternacoes(
        sessao, pagina=pagina, por_pagina=por_pagina, janela_dias=janela_dias
    )
    return Pagina(
        itens=[ItemReinternacao(**i) for i in itens],
        total=total,
        pagina=pagina,
        por_pagina=por_pagina,
    )
