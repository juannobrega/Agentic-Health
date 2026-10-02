"""Agregações, coortes e dicionário (E3, E4).

Agregações em SQL direto — `count(DISTINCT)` com corte demográfico é mais claro
assim. A coorte usa ORM: é onde os filtros são dinâmicos e o risco de injection
se concentraria (ADR-006).
"""
from sqlalchemy import Integer, String, Text, bindparam, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from api import modelos

# condições tratadas como crônicas para a contagem de multimorbidade
CRONICAS = (
    "Hipertensão arterial",
    "Diabetes mellitus tipo 2",
    "Pré-diabetes",
    "Hiperlipidemia",
    "Asma",
    "Doença arterial coronariana",
    "Obesidade",
    "Síndrome metabólica",
)

JANELA_TEMPORAL = "1909 a janeiro de 2019"
AVISO_REPRESENTATIVIDADE = (
    "População sintética de Massachusetts, 75% branca. Inadequada para análise "
    "de equidade ou inferência epidemiológica."
)

MOTIVO_FILTRO_MEDICAMENTO = (
    "7.899 registros com código SNOMED de condição em vez de RxNorm foram "
    "excluídos (bug de ETL do dataset Synthea)"
)


# ------------------------------------------------------------- resumo


async def resumo_populacional(sessao: AsyncSession) -> dict:
    P = modelos.PessoaValida
    total = await sessao.scalar(select(func.count()).select_from(P)) or 0

    async def _agrupar(coluna):
        resultado = await sessao.execute(
            select(coluna, func.count())
            .select_from(P)
            .where(coluna.is_not(None))
            .group_by(coluna)
            .order_by(func.count().desc())
        )
        return [{"rotulo": r, "pacientes": n} for r, n in resultado.all()]

    piramide = await sessao.execute(
        text(
            """
            SELECT (idade / 10) * 10 AS decada, count(*) AS pacientes
              FROM synthea.vw_pessoa_valida
             WHERE idade IS NOT NULL
             GROUP BY decada ORDER BY decada
            """
        )
    )

    atendimentos = await sessao.execute(
        select(
            modelos.Atendimento.atendimento_descricao,
            func.count(),
        )
        .group_by(modelos.Atendimento.atendimento_descricao)
        .order_by(func.count().desc())
    )

    multimorbidade = await sessao.scalar(
        select(func.count()).select_from(
            select(modelos.Condicao.id_pessoa)
            .where(modelos.Condicao.nome_condicao.in_(CRONICAS))
            .group_by(modelos.Condicao.id_pessoa)
            .having(func.count(func.distinct(modelos.Condicao.nome_condicao)) >= 2)
            .subquery()
        )
    ) or 0

    return {
        "total_pacientes": total,
        "por_sexo": await _agrupar(P.sexo),
        "por_raca": await _agrupar(P.raca),
        "piramide_etaria": [
            {"faixa": f"{d}-{d + 9}", "pacientes": n} for d, n in piramide.all()
        ],
        "atendimentos_por_tipo": [
            {"rotulo": t or "não informado", "pacientes": n} for t, n in atendimentos.all()
        ],
        "pacientes_multimorbidade": multimorbidade,
        "janela_temporal": JANELA_TEMPORAL,
        "aviso_representatividade": AVISO_REPRESENTATIVIDADE,
    }


# -------------------------------------------------------- prevalência

# Distingue ocorrências de pacientes afetados: "Infecção viral das vias aéreas
# superiores" tem 1.134 ocorrências em 711 pacientes — reportar 1.134 como
# prevalência estaria errado.
_PREVALENCIA = """
SELECT e.{coluna} AS nome,
       count(*) AS ocorrencias,
       count(DISTINCT e.id_pessoa) AS pacientes
  FROM synthea.{tabela} e
  JOIN synthea.vw_pessoa_valida p ON p.id_pessoa = e.id_pessoa
 WHERE e.{coluna} IS NOT NULL
   AND (:sexo IS NULL OR p.sexo = :sexo)
   AND (:raca IS NULL OR p.raca = :raca)
   AND (:idade_min IS NULL OR p.idade >= :idade_min)
   AND (:idade_max IS NULL OR p.idade <= :idade_max)
 GROUP BY e.{coluna}
 ORDER BY {ordem}
 LIMIT :limite OFFSET :deslocamento
"""

_PREVALENCIA_TOTAL = """
SELECT count(DISTINCT e.{coluna})
  FROM synthea.{tabela} e
  JOIN synthea.vw_pessoa_valida p ON p.id_pessoa = e.id_pessoa
 WHERE e.{coluna} IS NOT NULL
   AND (:sexo IS NULL OR p.sexo = :sexo)
   AND (:raca IS NULL OR p.raca = :raca)
   AND (:idade_min IS NULL OR p.idade >= :idade_min)
   AND (:idade_max IS NULL OR p.idade <= :idade_max)
"""

_DENOMINADOR = """
SELECT count(*) FROM synthea.vw_pessoa_valida p
 WHERE (:sexo IS NULL OR p.sexo = :sexo)
   AND (:raca IS NULL OR p.raca = :raca)
   AND (:idade_min IS NULL OR p.idade >= :idade_min)
   AND (:idade_max IS NULL OR p.idade <= :idade_max)
"""

_BINDS_DEMOGRAFICOS = (
    bindparam("sexo", type_=Text),
    bindparam("raca", type_=Text),
    bindparam("idade_min", type_=Integer),
    bindparam("idade_max", type_=Integer),
)

# tabela e coluna por domínio — valores internos, nunca vindos do cliente
DOMINIOS_PREVALENCIA = {
    "condicoes": ("condicao", "nome_condicao", None),
    "medicamentos": ("vw_medicamento_valido", "nome_medicamento", MOTIVO_FILTRO_MEDICAMENTO),
    "procedimentos": ("procedimento", "nome_procedimento", None),
    "exames": ("exame", "nome_exame", "Exames sem resultado: o dataset não traz valores"),
}

ORDENS = {
    "pacientes": "pacientes DESC, nome",
    "ocorrencias": "ocorrencias DESC, nome",
    "nome": "nome",
}


async def prevalencia(
    sessao: AsyncSession,
    dominio: str,
    *,
    pagina: int = 1,
    por_pagina: int = 25,
    sexo: str | None = None,
    raca: str | None = None,
    idade_min: int | None = None,
    idade_max: int | None = None,
    ordenar_por: str = "pacientes",
) -> tuple[list[dict], int, int, str | None]:
    tabela, coluna, motivo = DOMINIOS_PREVALENCIA[dominio]
    ordem = ORDENS[ordenar_por]

    params = {
        "sexo": sexo,
        "raca": raca,
        "idade_min": idade_min,
        "idade_max": idade_max,
    }

    denominador = (
        await sessao.scalar(text(_DENOMINADOR).bindparams(*_BINDS_DEMOGRAFICOS), params)
        or 0
    )
    total = (
        await sessao.scalar(
            text(_PREVALENCIA_TOTAL.format(tabela=tabela, coluna=coluna)).bindparams(
                *_BINDS_DEMOGRAFICOS
            ),
            params,
        )
        or 0
    )
    resultado = await sessao.execute(
        text(
            _PREVALENCIA.format(tabela=tabela, coluna=coluna, ordem=ordem)
        ).bindparams(*_BINDS_DEMOGRAFICOS),
        {**params, "limite": por_pagina, "deslocamento": (pagina - 1) * por_pagina},
    )
    itens = [dict(l) for l in resultado.mappings()]
    for item in itens:
        item["percentual_pacientes"] = (
            round(100 * item["pacientes"] / denominador, 2) if denominador else 0.0
        )
    return itens, total, denominador, motivo


# -------------------------------------------------------------- coorte


def _montar_consulta_coorte(criterios):
    """Compõe a consulta via ORM — sem concatenação de string (ADR-006)."""
    P = modelos.PessoaValida
    consulta = select(P)
    descricoes: list[str] = []

    if criterios.sexo:
        consulta = consulta.where(P.sexo == criterios.sexo)
        descricoes.append(f"sexo = {criterios.sexo}")
    if criterios.raca:
        consulta = consulta.where(P.raca == criterios.raca)
        descricoes.append(f"raça = {criterios.raca}")
    if criterios.idade_min is not None:
        consulta = consulta.where(P.idade >= criterios.idade_min)
        descricoes.append(f"idade >= {criterios.idade_min}")
    if criterios.idade_max is not None:
        consulta = consulta.where(P.idade <= criterios.idade_max)
        descricoes.append(f"idade <= {criterios.idade_max}")

    if criterios.condicoes:
        if criterios.condicoes_todas:
            # exige TODAS: conta quantas distintas o paciente tem
            sub = (
                select(modelos.Condicao.id_pessoa)
                .where(modelos.Condicao.nome_condicao.in_(criterios.condicoes))
                .group_by(modelos.Condicao.id_pessoa)
                .having(
                    func.count(func.distinct(modelos.Condicao.nome_condicao))
                    == len(set(criterios.condicoes))
                )
            )
            descricoes.append(f"todas as condições: {', '.join(criterios.condicoes)}")
        else:
            sub = select(modelos.Condicao.id_pessoa).where(
                modelos.Condicao.nome_condicao.in_(criterios.condicoes)
            )
            descricoes.append(f"qualquer condição: {', '.join(criterios.condicoes)}")
        consulta = consulta.where(P.id_pessoa.in_(sub))

    if criterios.medicamentos:
        consulta = consulta.where(
            P.id_pessoa.in_(
                select(modelos.MedicamentoValido.id_pessoa).where(
                    modelos.MedicamentoValido.nome_medicamento.in_(criterios.medicamentos)
                )
            )
        )
        descricoes.append(f"medicamentos: {', '.join(criterios.medicamentos)}")

    if criterios.tipo_atendimento:
        consulta = consulta.where(
            P.id_pessoa.in_(
                select(modelos.Atendimento.id_pessoa).where(
                    modelos.Atendimento.atendimento_descricao
                    == criterios.tipo_atendimento
                )
            )
        )
        descricoes.append(f"tipo de atendimento: {criterios.tipo_atendimento}")

    # filtros de qualidade sempre ativos — declarados, não escondidos (ADR-008)
    descricoes.append("[qualidade] exclui 2 pacientes com nascimento implausível")
    if criterios.medicamentos:
        descricoes.append(f"[qualidade] {MOTIVO_FILTRO_MEDICAMENTO}")

    return consulta, descricoes


async def contar_coorte(sessao: AsyncSession, criterios) -> tuple[int, list[str]]:
    consulta, descricoes = _montar_consulta_coorte(criterios)
    total = await sessao.scalar(select(func.count()).select_from(consulta.subquery())) or 0
    return total, descricoes


async def montar_coorte(
    sessao: AsyncSession, criterios, *, pagina: int = 1, por_pagina: int = 25
) -> tuple[list, int, list[str]]:
    consulta, descricoes = _montar_consulta_coorte(criterios)
    total = await sessao.scalar(select(func.count()).select_from(consulta.subquery())) or 0
    consulta = (
        consulta.order_by(modelos.PessoaValida.id_pessoa)
        .limit(por_pagina)
        .offset((pagina - 1) * por_pagina)
    )
    return list((await sessao.scalars(consulta)).all()), total, descricoes


async def nomes_validos(sessao: AsyncSession, dominio: str) -> set[str]:
    """Nomes existentes, para validar critérios antes de retornar coorte vazia."""
    tabela, coluna, _ = DOMINIOS_PREVALENCIA[dominio]
    modelo = {
        "condicoes": modelos.Condicao.nome_condicao,
        "medicamentos": modelos.MedicamentoValido.nome_medicamento,
    }[dominio]
    return {n for (n,) in (await sessao.execute(select(modelo).distinct())).all() if n}


# ---------------------------------------------------------- dicionário


async def listar_dicionario(
    sessao: AsyncSession,
    *,
    pagina: int = 1,
    por_pagina: int = 50,
    vocabulario: str | None = None,
    dominio: str | None = None,
    termo: str | None = None,
) -> tuple[list, int]:
    D = modelos.DicionarioConceito
    consulta = select(D)

    if vocabulario:
        consulta = consulta.where(D.vocabulario == vocabulario)
    if dominio:
        consulta = consulta.where(D.dominios.like(f"%{dominio}%"))
    if termo:
        padrao = f"%{termo}%"
        consulta = consulta.where(
            func.unaccent(func.lower(D.nome_portugues)).like(
                func.unaccent(func.lower(padrao))
            )
            | D.codigo_origem.like(padrao)
        )

    total = await sessao.scalar(select(func.count()).select_from(consulta.subquery())) or 0
    consulta = (
        consulta.order_by(D.ocorrencias.desc().nullslast(), D.codigo_origem)
        .limit(por_pagina)
        .offset((pagina - 1) * por_pagina)
    )
    return list((await sessao.scalars(consulta)).all()), total


async def obter_conceito(sessao: AsyncSession, codigo: str):
    return await sessao.scalar(
        select(modelos.DicionarioConceito).where(
            modelos.DicionarioConceito.codigo_origem == codigo
        )
    )


# ------------------------------------------------------------- busca

LIMITE_BUSCA = 20

_CAMPOS_BUSCA = {
    "condicoes": modelos.Condicao.nome_condicao,
    "medicamentos": modelos.MedicamentoValido.nome_medicamento,
    "procedimentos": modelos.Procedimento.nome_procedimento,
    "exames": modelos.Exame.nome_exame,
    "observacoes": modelos.Observacao.nome_observacao,
}


async def buscar(sessao: AsyncSession, termo: str) -> tuple[dict[str, list[str]], bool]:
    """Busca nos nomes clínicos, ignorando acento e caixa.

    O banco usa locale C, então ILIKE não normaliza acento: "pre-diabetes"
    precisa achar "Pré-diabetes". Daí o unaccent (ADR-002).
    """
    padrao = f"%{termo}%"
    resultados: dict[str, list[str]] = {}
    truncado = False

    for chave, coluna in _CAMPOS_BUSCA.items():
        consulta = (
            select(coluna, func.count().label("n"))
            .where(
                coluna.is_not(None),
                func.unaccent(func.lower(coluna)).like(
                    func.unaccent(func.lower(padrao))
                ),
            )
            .group_by(coluna)
            .order_by(func.count().desc())
            .limit(LIMITE_BUSCA + 1)
        )
        nomes = [n for n, _ in (await sessao.execute(consulta)).all()]
        if len(nomes) > LIMITE_BUSCA:
            truncado = True
            nomes = nomes[:LIMITE_BUSCA]
        resultados[chave] = nomes

    return resultados, truncado


async def sugestoes(
    sessao: AsyncSession, dominio: str, termo: str, limite: int = 10
) -> list[dict]:
    """Autocomplete: os mais frequentes primeiro."""
    coluna = _CAMPOS_BUSCA[dominio]
    padrao = f"%{termo}%"
    resultado = await sessao.execute(
        select(coluna, func.count().label("n"))
        .where(
            coluna.is_not(None),
            func.unaccent(func.lower(coluna)).like(func.unaccent(func.lower(padrao))),
        )
        .group_by(coluna)
        .order_by(func.count().desc())
        .limit(limite)
    )
    return [{"nome": n, "ocorrencias": c} for n, c in resultado.all()]
