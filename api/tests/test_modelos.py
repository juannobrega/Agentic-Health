"""Garantias estruturais dos modelos ORM (ADR-006).

O teste de chave substituta é o mais importante do arquivo: declarar o ID
original como primary key faria o SQLAlchemy tratar linhas distintas como a
mesma entidade — corrupção silenciosa.
"""
import pytest
from sqlalchemy import func, inspect, select

from api import modelos
from api.modelos import (
    Base,
    Condicao,
    Exame,
    ExposicaoMedicamento,
    MedicamentoValido,
    Observacao,
    Pessoa,
    PessoaValida,
    Visao,
)

# tabelas cujo ID original é duplicado no dataset Synthea (ADR-002)
TABELAS_CHAVE_SUBSTITUTA = {
    Exame: "id_exame",
    ExposicaoMedicamento: "id_exposicao_medicamento",
    Observacao: "id_observacao",
}


@pytest.mark.parametrize("modelo,coluna_id", TABELAS_CHAVE_SUBSTITUTA.items())
def test_chave_substituta_e_a_primary_key(modelo, coluna_id):
    """`pk` é a PK; o ID original NÃO pode ser primary key."""
    pks = {c.name for c in inspect(modelo).mapper.primary_key}
    assert pks == {"pk"}, (
        f"{modelo.__name__}: PK deveria ser apenas 'pk', veio {pks}. "
        f"O dataset repete {coluna_id} em registros clínicos distintos (ADR-002)."
    )


@pytest.mark.parametrize("modelo,coluna_id", TABELAS_CHAVE_SUBSTITUTA.items())
def test_id_original_nao_tem_unicidade(modelo, coluna_id):
    coluna = modelo.__table__.columns[coluna_id]
    assert not coluna.unique, (
        f"{modelo.__name__}.{coluna_id} não pode ser UNIQUE — o dataset repete valores."
    )
    assert not coluna.primary_key


def test_condicao_usa_pk_natural():
    """condicao não tem duplicata: o ID original é a PK."""
    pks = {c.name for c in inspect(Condicao).mapper.primary_key}
    assert pks == {"id_condicao"}


def test_relacionamentos_usam_lazy_raise():
    """lazy='raise' previne N+1 silencioso (ADR-006)."""
    for modelo in (Pessoa, modelos.Atendimento, Condicao, modelos.Procedimento):
        for nome, rel in inspect(modelo).mapper.relationships.items():
            assert rel.lazy == "raise", (
                f"{modelo.__name__}.{nome} deveria usar lazy='raise' para "
                f"impedir carregamento implícito."
            )


def test_views_marcadas_como_visao():
    """As views precisam ser reconhecíveis para o Alembic ignorá-las."""
    for modelo in (PessoaValida, MedicamentoValido, modelos.AtendimentoResumo):
        assert issubclass(modelo, Visao), f"{modelo.__name__} deveria herdar de Visao"


def test_modelos_no_schema_correto():
    assert Base.metadata.schema == "synthea"
    assert Pessoa.__table__.schema == "synthea"


@pytest.mark.asyncio
async def test_modelos_batem_com_o_banco(sessao):
    """Cada modelo deve ser consultável: pega divergência de coluna (ADR-006)."""
    for modelo in (
        Pessoa,
        PessoaValida,
        modelos.PeriodoObservacao,
        modelos.Atendimento,
        modelos.AtendimentoResumo,
        Condicao,
        modelos.Procedimento,
        ExposicaoMedicamento,
        MedicamentoValido,
        Exame,
        Observacao,
        modelos.PeriodoCondicao,
        modelos.PeriodoMedicamento,
        modelos.DicionarioConceito,
    ):
        await sessao.execute(select(modelo).limit(1))


@pytest.mark.asyncio
async def test_contagens_do_dataset(sessao):
    """Premissas do dataset carregado (ADR-002)."""
    esperado = [
        (Pessoa, 1130),
        (modelos.Atendimento, 32153),
        (Condicao, 7900),
        (ExposicaoMedicamento, 29518),
        (modelos.Procedimento, 17333),
        (Exame, 199514),
        (Observacao, 8518),
        (modelos.DicionarioConceito, 535),
    ]
    for modelo, qtd in esperado:
        total = await sessao.scalar(select(func.count()).select_from(modelo))
        assert total == qtd, f"{modelo.__tablename__}: esperado {qtd}, veio {total}"


@pytest.mark.asyncio
async def test_exames_nao_tem_valor_numerico(sessao):
    """Limitação estrutural: os resultados se perderam no ETL (ADR-008)."""
    com_valor = await sessao.scalar(
        select(func.count()).select_from(Exame).where(Exame.valor_numerico.is_not(None))
    )
    assert com_valor == 0


@pytest.mark.asyncio
async def test_medicamentos_invalidos_estao_marcados(sessao):
    """7.899 linhas trazem código SNOMED de condição (ADR-008)."""
    invalidos = await sessao.scalar(
        select(func.count())
        .select_from(ExposicaoMedicamento)
        .where(ExposicaoMedicamento.inconsistencia_vocabulario.is_not(None))
    )
    assert invalidos == 7899

    validos = await sessao.scalar(select(func.count()).select_from(MedicamentoValido))
    assert validos == 21619


@pytest.mark.asyncio
async def test_view_de_pessoa_exclui_nascimentos_implausiveis(sessao):
    """IDs 265 (2099) e 332 (1099) ficam fora (ADR-008)."""
    validos = await sessao.scalar(select(func.count()).select_from(PessoaValida))
    assert validos == 1128


@pytest.mark.asyncio
async def test_ids_originais_realmente_duplicam(sessao):
    """Confirma a premissa que justifica a chave substituta (ADR-002)."""
    for modelo, coluna_id in TABELAS_CHAVE_SUBSTITUTA.items():
        coluna = getattr(modelo, coluna_id)
        total = await sessao.scalar(select(func.count()).select_from(modelo))
        distintos = await sessao.scalar(select(func.count(func.distinct(coluna))))
        assert distintos < total, (
            f"{modelo.__tablename__}: esperava IDs duplicados, "
            f"mas {coluna_id} tem {distintos} distintos em {total} linhas."
        )
