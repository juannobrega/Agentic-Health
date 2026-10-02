"""Endpoints de paciente e prontuário (E1)."""
from datetime import date
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession

from api.db import obter_sessao
from api.esquemas.comum import FiltroQualidade, Pagina
from api.esquemas.paciente import (
    ContadoresPaciente,
    EventoTimeline,
    ItemAlergia,
    ItemCondicao,
    ItemExame,
    ItemMedicamento,
    ItemProcedimento,
    JanelaObservacao,
    ListaMedicamentos,
    PacienteDetalhe,
    PacienteResumo,
)
from api.repositorios import paciente as repo

roteador = APIRouter(prefix="/pacientes", tags=["pacientes"])

IdPessoa = Annotated[int, Path(ge=1, description="Identificador do paciente")]
ParamPagina = Annotated[int, Query(ge=1)]
ParamPorPagina = Annotated[int, Query(ge=1, le=100)]


@roteador.get(
    "",
    response_model=Pagina[PacienteResumo],
    summary="Listar pacientes",
    description=(
        "Lista paginada com filtros combináveis. Exclui por padrão os 2 pacientes "
        "com ano de nascimento implausível, retornando 1.128 de 1.130.\n\n"
        "Não há busca por nome: o OMOP CDM é desidentificado e a tabela de "
        "pessoa não tem esse campo (ADR-009)."
    ),
)
async def listar_pacientes(
    sessao: Annotated[AsyncSession, Depends(obter_sessao)],
    pagina: ParamPagina = 1,
    por_pagina: ParamPorPagina = 25,
    sexo: Annotated[Literal["M", "F"] | None, Query()] = None,
    raca: Annotated[str | None, Query(description="branca, preta, amarela…")] = None,
    etnia: Annotated[str | None, Query()] = None,
    idade_min: Annotated[int | None, Query(ge=0, le=130)] = None,
    idade_max: Annotated[int | None, Query(ge=0, le=130)] = None,
    condicao: Annotated[
        str | None, Query(description="Nome clínico exato, em português")
    ] = None,
    ordenar_por: Annotated[Literal["id_pessoa", "idade"], Query()] = "id_pessoa",
    decrescente: Annotated[bool, Query()] = False,
) -> Pagina[PacienteResumo]:
    if idade_min is not None and idade_max is not None and idade_min > idade_max:
        raise HTTPException(400, "idade_min não pode ser maior que idade_max")

    itens, total = await repo.listar(
        sessao,
        pagina=pagina,
        por_pagina=por_pagina,
        sexo=sexo,
        raca=raca,
        etnia=etnia,
        idade_min=idade_min,
        idade_max=idade_max,
        condicao=condicao,
        ordenar_por=ordenar_por,
        decrescente=decrescente,
    )
    return Pagina(
        itens=[PacienteResumo.model_validate(i) for i in itens],
        total=total,
        pagina=pagina,
        por_pagina=por_pagina,
    )


@roteador.get(
    "/{id_pessoa}",
    response_model=PacienteDetalhe,
    summary="Detalhe do paciente",
)
async def obter_paciente(
    id_pessoa: IdPessoa,
    sessao: Annotated[AsyncSession, Depends(obter_sessao)],
) -> PacienteDetalhe:
    pessoa = await repo.obter(sessao, id_pessoa)
    if pessoa is None:
        raise HTTPException(404, f"Paciente {id_pessoa} não encontrado")

    idade = await repo.obter_idade(sessao, id_pessoa)
    contadores = await repo.contar_eventos(sessao, id_pessoa)
    janela = await repo.obter_janela_observacao(sessao, id_pessoa)

    # ano de nascimento implausível fica fora da view, então idade vem nula
    aviso = None
    if idade is None:
        aviso = (
            f"Ano de nascimento implausível ({pessoa.ano_nascimento}); "
            f"a idade não pôde ser calculada."
        )

    return PacienteDetalhe(
        id_pessoa=pessoa.id_pessoa,
        codigo_origem_pessoa=pessoa.codigo_origem_pessoa,
        sexo=pessoa.sexo,
        idade=idade,
        raca=pessoa.raca,
        etnia=pessoa.etnia,
        ano_nascimento=pessoa.ano_nascimento,
        sexo_descricao=pessoa.sexo_descricao,
        raca_descricao=pessoa.raca_descricao,
        janela_observacao=(
            JanelaObservacao(
                data_inicio=janela.data_inicio_periodo,
                data_fim=janela.data_fim_periodo,
            )
            if janela
            else None
        ),
        contadores=ContadoresPaciente(**contadores),
        aviso=aviso,
    )


@roteador.get(
    "/{id_pessoa}/timeline",
    response_model=Pagina[EventoTimeline],
    summary="Timeline clínica unificada",
    description=(
        "Condições, medicamentos, procedimentos e exames numa linha do tempo "
        "ordenada por data.\n\n"
        "Os eventos de exame vêm com `valor_disponivel: false` — o dataset não "
        "traz resultados (ADR-008). Medicamentos já filtrados."
    ),
)
async def obter_timeline(
    id_pessoa: IdPessoa,
    sessao: Annotated[AsyncSession, Depends(obter_sessao)],
    pagina: ParamPagina = 1,
    por_pagina: ParamPorPagina = 50,
    tipo: Annotated[
        list[Literal["condicao", "medicamento", "procedimento", "exame"]] | None,
        Query(description="Repita o parâmetro para múltiplos tipos"),
    ] = None,
    data_de: Annotated[date | None, Query()] = None,
    data_ate: Annotated[date | None, Query()] = None,
) -> Pagina[EventoTimeline]:
    if await repo.obter(sessao, id_pessoa) is None:
        raise HTTPException(404, f"Paciente {id_pessoa} não encontrado")

    eventos, total = await repo.timeline(
        sessao,
        id_pessoa,
        pagina=pagina,
        por_pagina=por_pagina,
        tipos=list(tipo) if tipo else None,
        data_de=data_de,
        data_ate=data_ate,
    )
    return Pagina(
        itens=[EventoTimeline(**e) for e in eventos],
        total=total,
        pagina=pagina,
        por_pagina=por_pagina,
    )


@roteador.get(
    "/{id_pessoa}/condicoes",
    response_model=Pagina[ItemCondicao],
    summary="Condições do paciente",
)
async def listar_condicoes(
    id_pessoa: IdPessoa,
    sessao: Annotated[AsyncSession, Depends(obter_sessao)],
    pagina: ParamPagina = 1,
    por_pagina: ParamPorPagina = 25,
) -> Pagina[ItemCondicao]:
    if await repo.obter(sessao, id_pessoa) is None:
        raise HTTPException(404, f"Paciente {id_pessoa} não encontrado")
    itens, total = await repo.listar_condicoes(sessao, id_pessoa, pagina, por_pagina)
    return Pagina(
        itens=[ItemCondicao.model_validate(i) for i in itens],
        total=total,
        pagina=pagina,
        por_pagina=por_pagina,
    )


@roteador.get(
    "/{id_pessoa}/medicamentos",
    response_model=ListaMedicamentos,
    summary="Medicamentos do paciente",
    description=(
        "Apenas medicamentos RxNorm válidos. A resposta declara quantos "
        "registros foram excluídos por trazerem código de condição (ADR-008)."
    ),
)
async def listar_medicamentos(
    id_pessoa: IdPessoa,
    sessao: Annotated[AsyncSession, Depends(obter_sessao)],
    pagina: ParamPagina = 1,
    por_pagina: ParamPorPagina = 25,
) -> ListaMedicamentos:
    if await repo.obter(sessao, id_pessoa) is None:
        raise HTTPException(404, f"Paciente {id_pessoa} não encontrado")
    itens, total, excluidos = await repo.listar_medicamentos(
        sessao, id_pessoa, pagina, por_pagina
    )
    return ListaMedicamentos(
        itens=[ItemMedicamento.model_validate(i) for i in itens],
        total=total,
        pagina=pagina,
        por_pagina=por_pagina,
        filtro_qualidade=FiltroQualidade(
            descricao=repo.MOTIVO_FILTRO_MEDICAMENTO,
            registros_excluidos=excluidos,
        ),
    )


@roteador.get(
    "/{id_pessoa}/procedimentos",
    response_model=Pagina[ItemProcedimento],
    summary="Procedimentos do paciente",
)
async def listar_procedimentos(
    id_pessoa: IdPessoa,
    sessao: Annotated[AsyncSession, Depends(obter_sessao)],
    pagina: ParamPagina = 1,
    por_pagina: ParamPorPagina = 25,
) -> Pagina[ItemProcedimento]:
    if await repo.obter(sessao, id_pessoa) is None:
        raise HTTPException(404, f"Paciente {id_pessoa} não encontrado")
    itens, total = await repo.listar_procedimentos(
        sessao, id_pessoa, pagina, por_pagina
    )
    return Pagina(
        itens=[ItemProcedimento.model_validate(i) for i in itens],
        total=total,
        pagina=pagina,
        por_pagina=por_pagina,
    )


@roteador.get(
    "/{id_pessoa}/exames",
    response_model=Pagina[ItemExame],
    summary="Exames do paciente",
    description=(
        "Exames pedidos. **O dataset não traz resultados**: `valor_numerico` é "
        "sempre nulo. A UI deve exibir 'não disponível', nunca vazio (ADR-008)."
    ),
)
async def listar_exames(
    id_pessoa: IdPessoa,
    sessao: Annotated[AsyncSession, Depends(obter_sessao)],
    pagina: ParamPagina = 1,
    por_pagina: ParamPorPagina = 25,
) -> Pagina[ItemExame]:
    if await repo.obter(sessao, id_pessoa) is None:
        raise HTTPException(404, f"Paciente {id_pessoa} não encontrado")
    itens, total = await repo.listar_exames(sessao, id_pessoa, pagina, por_pagina)
    return Pagina(
        itens=[ItemExame.model_validate(i) for i in itens],
        total=total,
        pagina=pagina,
        por_pagina=por_pagina,
    )


@roteador.get(
    "/{id_pessoa}/alergias",
    response_model=list[ItemAlergia],
    summary="Alergias do paciente",
    description="Lista vazia quando não há alergia registrada — não é erro.",
)
async def listar_alergias(
    id_pessoa: IdPessoa,
    sessao: Annotated[AsyncSession, Depends(obter_sessao)],
) -> list[ItemAlergia]:
    if await repo.obter(sessao, id_pessoa) is None:
        raise HTTPException(404, f"Paciente {id_pessoa} não encontrado")
    return [
        ItemAlergia.model_validate(a) for a in await repo.listar_alergias(sessao, id_pessoa)
    ]
