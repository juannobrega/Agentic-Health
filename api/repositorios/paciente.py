"""Acesso a dados de paciente (E1).

ORM nos filtros dinâmicos — a composição de `where()` elimina o risco de
injection que a concatenação de string traria (ADR-006). A timeline fica em SQL
direto porque o UNION de 4 domínios é mais legível assim.
"""
from datetime import date

from sqlalchemy import ARRAY, Date, String, bindparam, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from api import modelos

# Ordenação mapeada a atributo do modelo, nunca a nome de coluna vindo do
# cliente (ADR-006).
COLUNAS_ORDENAVEIS = {
    "id_pessoa": modelos.PessoaValida.id_pessoa,
    "idade": modelos.PessoaValida.idade,
}

# As 7.899 linhas excluídas trazem código SNOMED de condição (ADR-008)
MOTIVO_FILTRO_MEDICAMENTO = (
    "Registros com código SNOMED de condição em vez de RxNorm foram excluídos "
    "(bug de ETL do dataset Synthea)"
)


async def listar(
    sessao: AsyncSession,
    *,
    pagina: int = 1,
    por_pagina: int = 25,
    sexo: str | None = None,
    raca: str | None = None,
    etnia: str | None = None,
    idade_min: int | None = None,
    idade_max: int | None = None,
    condicao: str | None = None,
    ordenar_por: str = "id_pessoa",
    decrescente: bool = False,
) -> tuple[list[modelos.PessoaValida], int]:
    """Lista pacientes com filtros combináveis.

    Usa vw_pessoa_valida, que exclui os 2 anos de nascimento impossíveis.
    """
    P = modelos.PessoaValida
    consulta = select(P)

    if sexo:
        consulta = consulta.where(P.sexo == sexo)
    if raca:
        consulta = consulta.where(P.raca == raca)
    if etnia:
        consulta = consulta.where(P.etnia == etnia)
    if idade_min is not None:
        consulta = consulta.where(P.idade >= idade_min)
    if idade_max is not None:
        consulta = consulta.where(P.idade <= idade_max)
    if condicao:
        consulta = consulta.where(
            P.id_pessoa.in_(
                select(modelos.Condicao.id_pessoa).where(
                    modelos.Condicao.nome_condicao == condicao
                )
            )
        )

    total = await sessao.scalar(
        select(func.count()).select_from(consulta.subquery())
    ) or 0

    coluna = COLUNAS_ORDENAVEIS[ordenar_por]
    consulta = consulta.order_by(coluna.desc() if decrescente else coluna.asc())
    consulta = consulta.limit(por_pagina).offset((pagina - 1) * por_pagina)

    itens = list((await sessao.scalars(consulta)).all())
    return itens, total


async def obter(sessao: AsyncSession, id_pessoa: int) -> modelos.Pessoa | None:
    return await sessao.scalar(
        select(modelos.Pessoa).where(modelos.Pessoa.id_pessoa == id_pessoa)
    )


async def obter_idade(sessao: AsyncSession, id_pessoa: int) -> int | None:
    """Idade da view; None se o ano de nascimento for implausível."""
    return await sessao.scalar(
        select(modelos.PessoaValida.idade).where(
            modelos.PessoaValida.id_pessoa == id_pessoa
        )
    )


async def contar_eventos(sessao: AsyncSession, id_pessoa: int) -> dict[str, int]:
    """Contadores por domínio. Medicamentos já filtrados (ADR-008)."""
    alvos = {
        "condicoes": modelos.Condicao,
        "medicamentos": modelos.MedicamentoValido,
        "procedimentos": modelos.Procedimento,
        "exames": modelos.Exame,
        "atendimentos": modelos.Atendimento,
    }
    contadores: dict[str, int] = {}
    for chave, modelo in alvos.items():
        contadores[chave] = (
            await sessao.scalar(
                select(func.count())
                .select_from(modelo)
                .where(modelo.id_pessoa == id_pessoa)
            )
            or 0
        )
    contadores["alergias"] = (
        await sessao.scalar(
            select(func.count())
            .select_from(modelos.Observacao)
            .where(
                modelos.Observacao.id_pessoa == id_pessoa,
                modelos.Observacao.nome_observacao.like("Alergia%"),
            )
        )
        or 0
    )
    return contadores


async def obter_janela_observacao(
    sessao: AsyncSession, id_pessoa: int
) -> modelos.PeriodoObservacao | None:
    return await sessao.scalar(
        select(modelos.PeriodoObservacao).where(
            modelos.PeriodoObservacao.id_pessoa == id_pessoa
        )
    )


# ---------------------------------------------------------------- timeline

# SQL direto: o UNION de 4 domínios é mais legível que o equivalente em ORM
# (ADR-006). Parâmetros nomeados, nunca f-string.
_TIMELINE = """
WITH eventos AS (
    SELECT 'condicao' AS tipo, data_inicio AS data, nome_condicao AS nome,
           id_atendimento, codigo_origem_condicao AS codigo_origem,
           id_condicao::bigint AS pk, true AS valor_disponivel
      FROM synthea.condicao WHERE id_pessoa = :id_pessoa
    UNION ALL
    SELECT 'medicamento', data_inicio, nome_medicamento,
           id_atendimento, codigo_origem_medicamento, pk, true
      FROM synthea.vw_medicamento_valido WHERE id_pessoa = :id_pessoa
    UNION ALL
    SELECT 'procedimento', data, nome_procedimento,
           id_atendimento, codigo_origem_procedimento,
           id_procedimento::bigint, true
      FROM synthea.procedimento WHERE id_pessoa = :id_pessoa
    UNION ALL
    -- valor_disponivel = false: o dataset não traz resultados (ADR-008)
    SELECT 'exame', data, nome_exame,
           id_atendimento, codigo_origem_exame, pk, false
      FROM synthea.exame WHERE id_pessoa = :id_pessoa
)
SELECT * FROM eventos
 WHERE (:tipos IS NULL OR tipo = ANY(:tipos))
   AND (:data_de IS NULL OR data >= :data_de)
   AND (:data_ate IS NULL OR data <= :data_ate)
 ORDER BY data DESC NULLS LAST, tipo
 LIMIT :limite OFFSET :deslocamento
"""

_TIMELINE_TOTAL = """
WITH eventos AS (
    SELECT 'condicao' AS tipo, data_inicio AS data FROM synthea.condicao
     WHERE id_pessoa = :id_pessoa
    UNION ALL
    SELECT 'medicamento', data_inicio FROM synthea.vw_medicamento_valido
     WHERE id_pessoa = :id_pessoa
    UNION ALL
    SELECT 'procedimento', data FROM synthea.procedimento
     WHERE id_pessoa = :id_pessoa
    UNION ALL
    SELECT 'exame', data FROM synthea.exame
     WHERE id_pessoa = :id_pessoa
)
SELECT count(*) FROM eventos
 WHERE (:tipos IS NULL OR tipo = ANY(:tipos))
   AND (:data_de IS NULL OR data >= :data_de)
   AND (:data_ate IS NULL OR data <= :data_ate)
"""

TIPOS_TIMELINE = ("condicao", "medicamento", "procedimento", "exame")

# O asyncpg precisa do tipo dos parâmetros opcionais: sem isso não sabe inferir
# o tipo de um NULL em `:tipos IS NULL`.
_BINDS_FILTRO = (
    bindparam("tipos", type_=ARRAY(String)),
    bindparam("data_de", type_=Date),
    bindparam("data_ate", type_=Date),
)

_CONSULTA_TIMELINE = text(_TIMELINE).bindparams(*_BINDS_FILTRO)
_CONSULTA_TIMELINE_TOTAL = text(_TIMELINE_TOTAL).bindparams(*_BINDS_FILTRO)


async def timeline(
    sessao: AsyncSession,
    id_pessoa: int,
    *,
    pagina: int = 1,
    por_pagina: int = 50,
    tipos: list[str] | None = None,
    data_de: date | None = None,
    data_ate: date | None = None,
) -> tuple[list[dict], int]:
    """Linha do tempo unificada, paginada — um paciente chega a 2.486 exames."""
    params = {
        "id_pessoa": id_pessoa,
        "tipos": tipos or None,
        "data_de": data_de,
        "data_ate": data_ate,
    }
    total = await sessao.scalar(_CONSULTA_TIMELINE_TOTAL, params) or 0
    resultado = await sessao.execute(
        _CONSULTA_TIMELINE,
        {**params, "limite": por_pagina, "deslocamento": (pagina - 1) * por_pagina},
    )
    return [dict(linha) for linha in resultado.mappings()], total


# ------------------------------------------------------------- por domínio


async def _listar_dominio(
    sessao: AsyncSession,
    modelo,
    id_pessoa: int,
    coluna_data,
    pagina: int,
    por_pagina: int,
) -> tuple[list, int]:
    total = (
        await sessao.scalar(
            select(func.count()).select_from(modelo).where(modelo.id_pessoa == id_pessoa)
        )
        or 0
    )
    consulta = (
        select(modelo)
        .where(modelo.id_pessoa == id_pessoa)
        .order_by(coluna_data.desc().nullslast())
        .limit(por_pagina)
        .offset((pagina - 1) * por_pagina)
    )
    return list((await sessao.scalars(consulta)).all()), total


async def listar_condicoes(sessao, id_pessoa, pagina=1, por_pagina=25):
    return await _listar_dominio(
        sessao, modelos.Condicao, id_pessoa,
        modelos.Condicao.data_inicio, pagina, por_pagina,
    )


async def listar_medicamentos(sessao, id_pessoa, pagina=1, por_pagina=25):
    """Só os válidos. Retorna também quantos foram excluídos (ADR-008)."""
    itens, total = await _listar_dominio(
        sessao, modelos.MedicamentoValido, id_pessoa,
        modelos.MedicamentoValido.data_inicio, pagina, por_pagina,
    )
    excluidos = (
        await sessao.scalar(
            select(func.count())
            .select_from(modelos.ExposicaoMedicamento)
            .where(
                modelos.ExposicaoMedicamento.id_pessoa == id_pessoa,
                modelos.ExposicaoMedicamento.inconsistencia_vocabulario.is_not(None),
            )
        )
        or 0
    )
    return itens, total, excluidos


async def listar_procedimentos(sessao, id_pessoa, pagina=1, por_pagina=25):
    return await _listar_dominio(
        sessao, modelos.Procedimento, id_pessoa,
        modelos.Procedimento.data, pagina, por_pagina,
    )


async def listar_exames(sessao, id_pessoa, pagina=1, por_pagina=25):
    return await _listar_dominio(
        sessao, modelos.Exame, id_pessoa, modelos.Exame.data, pagina, por_pagina,
    )


async def listar_alergias(sessao: AsyncSession, id_pessoa: int) -> list:
    """As 619 alergias são filtradas por nome: 83% dos conceitos não são
    mapeados no OMOP, então filtrar por concept_id não funciona (ADR-001)."""
    consulta = (
        select(modelos.Observacao)
        .where(
            modelos.Observacao.id_pessoa == id_pessoa,
            modelos.Observacao.nome_observacao.like("Alergia%"),
        )
        .order_by(modelos.Observacao.data.desc().nullslast())
    )
    return list((await sessao.scalars(consulta)).all())


# --------------------------------------------------------------- resumo


async def dados_para_resumo(sessao: AsyncSession, id_pessoa: int) -> dict:
    """Coleta o que o resumo clínico precisa, numa só passagem."""
    pessoa = await obter(sessao, id_pessoa)
    if pessoa is None:
        return {}

    condicoes = await sessao.execute(
        select(
            modelos.Condicao.nome_condicao,
            func.min(modelos.Condicao.data_inicio).label("primeira"),
            func.count().label("ocorrencias"),
        )
        .where(modelos.Condicao.id_pessoa == id_pessoa)
        .group_by(modelos.Condicao.nome_condicao)
        .order_by(func.min(modelos.Condicao.data_inicio).desc().nullslast())
    )

    medicamentos = await sessao.execute(
        select(
            modelos.MedicamentoValido.nome_medicamento,
            func.max(modelos.MedicamentoValido.data_inicio).label("ultima"),
        )
        .where(modelos.MedicamentoValido.id_pessoa == id_pessoa)
        .group_by(modelos.MedicamentoValido.nome_medicamento)
        .order_by(func.max(modelos.MedicamentoValido.data_inicio).desc().nullslast())
    )

    atendimentos = await sessao.execute(
        select(
            modelos.Atendimento.data_inicio,
            modelos.Atendimento.atendimento_descricao,
        )
        .where(modelos.Atendimento.id_pessoa == id_pessoa)
        .order_by(modelos.Atendimento.data_inicio.desc().nullslast())
        .limit(5)
    )

    return {
        "pessoa": pessoa,
        "idade": await obter_idade(sessao, id_pessoa),
        "janela": await obter_janela_observacao(sessao, id_pessoa),
        "contadores": await contar_eventos(sessao, id_pessoa),
        "condicoes": list(condicoes.all()),
        "medicamentos": list(medicamentos.all()),
        "alergias": await listar_alergias(sessao, id_pessoa),
        "atendimentos": list(atendimentos.all()),
    }
