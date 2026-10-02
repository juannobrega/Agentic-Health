"""Acesso a dados de atendimento e trajetória (E2)."""
from datetime import date

from sqlalchemy import Integer, bindparam, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from api import modelos

LIMITE_TRAJETORIA = 300  # a maior cadeia medida tem 250 passos


async def listar(
    sessao: AsyncSession,
    *,
    pagina: int = 1,
    por_pagina: int = 25,
    tipo: str | None = None,
    id_pessoa: int | None = None,
    data_de: date | None = None,
    data_ate: date | None = None,
    decrescente: bool = True,
) -> tuple[list, int]:
    A = modelos.Atendimento
    consulta = select(A)

    if tipo:
        consulta = consulta.where(A.atendimento_descricao == tipo)
    if id_pessoa is not None:
        consulta = consulta.where(A.id_pessoa == id_pessoa)
    if data_de is not None:
        consulta = consulta.where(A.data_inicio >= data_de)
    if data_ate is not None:
        consulta = consulta.where(A.data_inicio <= data_ate)

    total = await sessao.scalar(select(func.count()).select_from(consulta.subquery())) or 0

    ordem = A.data_inicio.desc().nullslast() if decrescente else A.data_inicio.asc()
    consulta = consulta.order_by(ordem, A.id_atendimento).limit(por_pagina).offset(
        (pagina - 1) * por_pagina
    )
    return list((await sessao.scalars(consulta)).all()), total


async def obter(sessao: AsyncSession, id_atendimento: int):
    return await sessao.scalar(
        select(modelos.Atendimento).where(
            modelos.Atendimento.id_atendimento == id_atendimento
        )
    )


async def eventos_do_atendimento(sessao: AsyncSession, id_atendimento: int) -> dict:
    """Condições, medicamentos, procedimentos e exames do atendimento."""
    async def _buscar(modelo, coluna_ordem):
        return list(
            (
                await sessao.scalars(
                    select(modelo)
                    .where(modelo.id_atendimento == id_atendimento)
                    .order_by(coluna_ordem.asc().nullsfirst())
                )
            ).all()
        )

    return {
        "condicoes": await _buscar(modelos.Condicao, modelos.Condicao.data_inicio),
        "medicamentos": await _buscar(
            modelos.MedicamentoValido, modelos.MedicamentoValido.data_inicio
        ),
        "procedimentos": await _buscar(modelos.Procedimento, modelos.Procedimento.data),
        "exames": await _buscar(modelos.Exame, modelos.Exame.data),
    }


# ----------------------------------------------------------- trajetória

# CTE recursiva: recursão é desajeitada no ORM, então fica em SQL (ADR-006).
# A coluna `visitados` acumula o caminho para detectar ciclo — nada no dataset
# garante que a cadeia de id_atendimento_anterior seja acíclica.
_TRAJETORIA = """
WITH RECURSIVE cadeia AS (
    SELECT a.id_atendimento,
           a.id_atendimento_anterior,
           a.atendimento_descricao,
           a.data_inicio,
           1 AS ordem,
           ARRAY[a.id_atendimento] AS visitados,
           false AS ciclo
      FROM synthea.atendimento a
     WHERE a.id_pessoa = :id_pessoa
       AND a.id_atendimento_anterior IS NULL

    UNION ALL

    SELECT prox.id_atendimento,
           prox.id_atendimento_anterior,
           prox.atendimento_descricao,
           prox.data_inicio,
           c.ordem + 1,
           c.visitados || prox.id_atendimento,
           prox.id_atendimento = ANY(c.visitados)
      FROM synthea.atendimento prox
      JOIN cadeia c ON prox.id_atendimento_anterior = c.id_atendimento
     WHERE NOT c.ciclo
       AND c.ordem < :limite
)
SELECT id_atendimento, atendimento_descricao AS tipo, data_inicio, ordem, ciclo
  FROM cadeia
 ORDER BY ordem, id_atendimento
"""

# Fallback: paciente cuja cadeia não tem raiz (todo atendimento tem predecessor)
# ou que não encadeia — devolve em ordem cronológica.
_SEM_CADEIA = """
SELECT id_atendimento, atendimento_descricao AS tipo, data_inicio,
       row_number() OVER (ORDER BY data_inicio NULLS FIRST, id_atendimento) AS ordem,
       false AS ciclo
  FROM synthea.atendimento
 WHERE id_pessoa = :id_pessoa
 ORDER BY ordem
 LIMIT :limite
"""


async def trajetoria(sessao: AsyncSession, id_pessoa: int) -> tuple[list[dict], bool, bool]:
    """Sequência encadeada de atendimentos. Devolve (passos, truncada, ciclo)."""
    params = {"id_pessoa": id_pessoa, "limite": LIMITE_TRAJETORIA}
    linhas = [dict(l) for l in (await sessao.execute(text(_TRAJETORIA), params)).mappings()]

    if not linhas:
        linhas = [
            dict(l) for l in (await sessao.execute(text(_SEM_CADEIA), params)).mappings()
        ]

    ciclo = any(l.get("ciclo") for l in linhas)
    truncada = len(linhas) >= LIMITE_TRAJETORIA
    return linhas, truncada, ciclo


async def condicoes_por_atendimento(
    sessao: AsyncSession, ids: list[int]
) -> dict[int, list[str]]:
    """Carrega as condições de vários atendimentos numa query — evita N+1."""
    if not ids:
        return {}
    resultado = await sessao.execute(
        select(modelos.Condicao.id_atendimento, modelos.Condicao.nome_condicao).where(
            modelos.Condicao.id_atendimento.in_(ids)
        )
    )
    mapa: dict[int, list[str]] = {}
    for id_atendimento, nome in resultado.all():
        if nome:
            mapa.setdefault(id_atendimento, []).append(nome)
    return mapa


# -------------------------------------------------------- reinternações

# "Reinternação" aqui é apenas mais de uma internação no histórico. NÃO é a
# definição clínica de readmissão em 30 dias.
_REINTERNACOES = """
WITH internacoes AS (
    SELECT id_pessoa, data_inicio,
           lag(data_inicio) OVER (PARTITION BY id_pessoa ORDER BY data_inicio) AS anterior
      FROM synthea.atendimento
     WHERE atendimento_descricao = 'Internação'
), intervalos AS (
    SELECT id_pessoa, (data_inicio - anterior) AS dias
      FROM internacoes WHERE anterior IS NOT NULL
)
SELECT p.id_pessoa, p.sexo, p.idade,
       (SELECT count(*) FROM synthea.atendimento a
         WHERE a.id_pessoa = p.id_pessoa
           AND a.atendimento_descricao = 'Internação') AS internacoes,
       min(i.dias) AS menor_intervalo_dias,
       max(i.dias) AS maior_intervalo_dias
  FROM intervalos i
  JOIN synthea.vw_pessoa_valida p USING (id_pessoa)
 GROUP BY p.id_pessoa, p.sexo, p.idade
HAVING (:janela_dias IS NULL OR min(i.dias) <= :janela_dias)
 ORDER BY internacoes DESC, menor_intervalo_dias ASC
 LIMIT :limite OFFSET :deslocamento
"""

_REINTERNACOES_TOTAL = """
WITH internacoes AS (
    SELECT id_pessoa, data_inicio,
           lag(data_inicio) OVER (PARTITION BY id_pessoa ORDER BY data_inicio) AS anterior
      FROM synthea.atendimento
     WHERE atendimento_descricao = 'Internação'
), intervalos AS (
    SELECT id_pessoa, (data_inicio - anterior) AS dias
      FROM internacoes WHERE anterior IS NOT NULL
)
SELECT count(*) FROM (
    SELECT id_pessoa FROM intervalos
     GROUP BY id_pessoa
    HAVING (:janela_dias IS NULL OR min(dias) <= :janela_dias)
) s
"""


# asyncpg não infere o tipo de um NULL em `:janela_dias IS NULL` — o tipo do
# bind precisa ser declarado (mesma causa do bind da timeline).
_CONSULTA_REINTERNACOES = text(_REINTERNACOES).bindparams(
    bindparam("janela_dias", type_=Integer)
)
_CONSULTA_REINTERNACOES_TOTAL = text(_REINTERNACOES_TOTAL).bindparams(
    bindparam("janela_dias", type_=Integer)
)


async def reinternacoes(
    sessao: AsyncSession,
    *,
    pagina: int = 1,
    por_pagina: int = 25,
    janela_dias: int | None = None,
) -> tuple[list[dict], int]:
    params = {"janela_dias": janela_dias}
    total = await sessao.scalar(_CONSULTA_REINTERNACOES_TOTAL, params) or 0
    resultado = await sessao.execute(
        _CONSULTA_REINTERNACOES,
        {**params, "limite": por_pagina, "deslocamento": (pagina - 1) * por_pagina},
    )
    return [dict(l) for l in resultado.mappings()], total
