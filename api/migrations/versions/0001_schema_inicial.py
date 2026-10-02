"""Schema inicial: reproduz Data/DB/sql/01_schema.sql e 02_indices.sql

As 11 tabelas do schema synthea e seus índices, conforme criados no bootstrap do
container (ADR-002).

Esta migration NÃO cria as views (ADR-006): elas vivem em
Data/DB/sql/03_views.sql e são aplicadas pelo initdb do Postgres. O
autogenerate as ignora via `include_object` em env.py.

Em exame, exposicao_medicamento e observacao a primary key é `pk` — o ID
original do dataset repete valores em registros clínicos distintos.

Revision ID: 0001
Revises:
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

ESQUEMA = "synthea"


def upgrade() -> None:
    # busca por nome clínico ignorando acento (locale C não normaliza)
    op.execute("CREATE EXTENSION IF NOT EXISTS unaccent")
    op.execute(f"CREATE SCHEMA IF NOT EXISTS {ESQUEMA}")

    op.create_table(
        "pessoa",
        sa.Column("id_pessoa", sa.Integer(), nullable=False),
        sa.Column("id_conceito_sexo", sa.Integer()),
        sa.Column("ano_nascimento", sa.Integer()),
        sa.Column("mes_nascimento", sa.Integer()),
        sa.Column("dia_nascimento", sa.Integer()),
        sa.Column("data_hora_nascimento", sa.DateTime()),
        sa.Column("id_conceito_raca", sa.Integer()),
        sa.Column("id_conceito_etnia", sa.Integer()),
        sa.Column("id_local", sa.Integer()),
        sa.Column("id_profissional", sa.Integer()),
        sa.Column("id_unidade_saude", sa.Integer()),
        sa.Column("codigo_origem_pessoa", sa.Text()),
        sa.Column("sexo", sa.Text()),
        sa.Column("id_conceito_origem_sexo", sa.Integer()),
        sa.Column("raca", sa.Text()),
        sa.Column("id_conceito_origem_raca", sa.Integer()),
        sa.Column("etnia", sa.Text()),
        sa.Column("id_conceito_origem_etnia", sa.Integer()),
        sa.Column("sexo_descricao", sa.Text()),
        sa.Column("raca_descricao", sa.Text()),
        sa.PrimaryKeyConstraint("id_pessoa"),
        schema=ESQUEMA,
    )

    op.create_table(
        "atendimento",
        sa.Column("id_atendimento", sa.Integer(), nullable=False),
        sa.Column("id_pessoa", sa.Integer(), nullable=False),
        sa.Column("id_conceito_atendimento", sa.Integer()),
        sa.Column("data_inicio", sa.Date()),
        sa.Column("data_hora_inicio", sa.DateTime()),
        sa.Column("data_fim", sa.Date()),
        sa.Column("data_hora_fim", sa.DateTime()),
        sa.Column("id_conceito_tipo_atendimento", sa.Integer()),
        sa.Column("id_profissional", sa.Integer()),
        sa.Column("id_unidade_saude", sa.Integer()),
        sa.Column("codigo_origem_atendimento", sa.Text()),
        sa.Column("id_conceito_origem_atendimento", sa.Integer()),
        sa.Column("id_conceito_origem_admissao", sa.Integer()),
        sa.Column("origem_admissao", sa.Text()),
        sa.Column("id_conceito_destino_alta", sa.Integer()),
        sa.Column("destino_alta", sa.Text()),
        sa.Column("id_atendimento_anterior", sa.Integer()),
        sa.Column("atendimento_descricao", sa.Text()),
        sa.ForeignKeyConstraint(["id_pessoa"], [f"{ESQUEMA}.pessoa.id_pessoa"]),
        sa.PrimaryKeyConstraint("id_atendimento"),
        schema=ESQUEMA,
    )
    op.create_index("ix_atendimento_pessoa", "atendimento", ["id_pessoa"], schema=ESQUEMA)
    op.create_index("ix_atendimento_data", "atendimento", ["data_inicio"], schema=ESQUEMA)

    op.create_table(
        "periodo_observacao",
        sa.Column("id_periodo_observacao", sa.Integer(), nullable=False),
        sa.Column("id_pessoa", sa.Integer(), nullable=False),
        sa.Column("data_inicio_periodo", sa.Date()),
        sa.Column("data_fim_periodo", sa.Date()),
        sa.Column("id_conceito_tipo_periodo", sa.Integer()),
        sa.ForeignKeyConstraint(["id_pessoa"], [f"{ESQUEMA}.pessoa.id_pessoa"]),
        sa.PrimaryKeyConstraint("id_periodo_observacao"),
        schema=ESQUEMA,
    )
    op.create_index("ix_periodo_obs_pessoa", "periodo_observacao", ["id_pessoa"], schema=ESQUEMA)

    op.create_table(
        "condicao",
        sa.Column("id_condicao", sa.Integer(), nullable=False),
        sa.Column("id_pessoa", sa.Integer(), nullable=False),
        sa.Column("id_conceito_condicao", sa.Integer()),
        sa.Column("data_inicio", sa.Date()),
        sa.Column("data_hora_inicio", sa.DateTime()),
        sa.Column("data_fim", sa.Date()),
        sa.Column("data_hora_fim", sa.DateTime()),
        sa.Column("id_conceito_tipo_condicao", sa.Integer()),
        sa.Column("motivo_interrupcao", sa.Text()),
        sa.Column("id_profissional", sa.Integer()),
        sa.Column("id_atendimento", sa.Integer()),
        sa.Column("id_detalhe_atendimento", sa.Integer()),
        sa.Column("codigo_origem_condicao", sa.Text()),
        sa.Column("id_conceito_origem_condicao", sa.Integer()),
        sa.Column("situacao_condicao", sa.Text()),
        sa.Column("id_conceito_situacao", sa.Integer()),
        sa.Column("nome_condicao", sa.Text()),
        sa.ForeignKeyConstraint(["id_atendimento"], [f"{ESQUEMA}.atendimento.id_atendimento"]),
        sa.ForeignKeyConstraint(["id_pessoa"], [f"{ESQUEMA}.pessoa.id_pessoa"]),
        sa.PrimaryKeyConstraint("id_condicao"),
        schema=ESQUEMA,
    )
    for nome, colunas in (
        ("ix_condicao_pessoa", ["id_pessoa"]),
        ("ix_condicao_atendimento", ["id_atendimento"]),
        ("ix_condicao_conceito", ["id_conceito_condicao"]),
        ("ix_condicao_nome", ["nome_condicao"]),
        ("ix_condicao_data", ["data_inicio"]),
    ):
        op.create_index(nome, "condicao", colunas, schema=ESQUEMA)

    # pk substituta: id_exposicao_medicamento repete 7.899 vezes (ADR-002)
    op.create_table(
        "exposicao_medicamento",
        sa.Column("pk", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("id_exposicao_medicamento", sa.Integer(), nullable=False),
        sa.Column("id_pessoa", sa.Integer(), nullable=False),
        sa.Column("id_conceito_medicamento", sa.Integer()),
        sa.Column("data_inicio", sa.Date()),
        sa.Column("data_hora_inicio", sa.DateTime()),
        sa.Column("data_fim", sa.Date()),
        sa.Column("data_hora_fim", sa.DateTime()),
        sa.Column("data_fim_literal", sa.Date()),
        sa.Column("id_conceito_tipo_medicamento", sa.Integer()),
        sa.Column("motivo_interrupcao", sa.Text()),
        sa.Column("reposicoes", sa.Integer()),
        sa.Column("quantidade", sa.Numeric()),
        sa.Column("dias_fornecimento", sa.Integer()),
        sa.Column("posologia", sa.Text()),
        sa.Column("id_conceito_via", sa.Integer()),
        sa.Column("numero_lote", sa.Text()),
        sa.Column("id_profissional", sa.Integer()),
        sa.Column("id_atendimento", sa.Integer()),
        sa.Column("id_detalhe_atendimento", sa.Integer()),
        sa.Column("codigo_origem_medicamento", sa.Text()),
        sa.Column("id_conceito_origem_medicamento", sa.Integer()),
        sa.Column("via_administracao", sa.Text()),
        sa.Column("unidade_dose", sa.Text()),
        sa.Column("nome_medicamento", sa.Text()),
        sa.Column("inconsistencia_vocabulario", sa.Text()),
        sa.ForeignKeyConstraint(["id_atendimento"], [f"{ESQUEMA}.atendimento.id_atendimento"]),
        sa.ForeignKeyConstraint(["id_pessoa"], [f"{ESQUEMA}.pessoa.id_pessoa"]),
        sa.PrimaryKeyConstraint("pk"),
        schema=ESQUEMA,
    )
    for nome, colunas in (
        ("ix_medicamento_pessoa", ["id_pessoa"]),
        ("ix_medicamento_atendimento", ["id_atendimento"]),
        ("ix_medicamento_nome", ["nome_medicamento"]),
        ("ix_medicamento_id_origem", ["id_exposicao_medicamento"]),
    ):
        op.create_index(nome, "exposicao_medicamento", colunas, schema=ESQUEMA)
    op.create_index(
        "ix_medicamento_validos",
        "exposicao_medicamento",
        ["id_pessoa"],
        schema=ESQUEMA,
        postgresql_where=sa.text("inconsistencia_vocabulario IS NULL"),
    )

    op.create_table(
        "procedimento",
        sa.Column("id_procedimento", sa.Integer(), nullable=False),
        sa.Column("id_pessoa", sa.Integer(), nullable=False),
        sa.Column("id_conceito_procedimento", sa.Integer()),
        sa.Column("data", sa.Date()),
        sa.Column("data_hora", sa.DateTime()),
        sa.Column("id_conceito_tipo_procedimento", sa.Integer()),
        sa.Column("id_conceito_modificador", sa.Integer()),
        sa.Column("quantidade", sa.Numeric()),
        sa.Column("id_profissional", sa.Integer()),
        sa.Column("id_atendimento", sa.Integer()),
        sa.Column("id_detalhe_atendimento", sa.Integer()),
        sa.Column("codigo_origem_procedimento", sa.Text()),
        sa.Column("id_conceito_origem_procedimento", sa.Integer()),
        sa.Column("modificador", sa.Text()),
        sa.Column("nome_procedimento", sa.Text()),
        sa.ForeignKeyConstraint(["id_atendimento"], [f"{ESQUEMA}.atendimento.id_atendimento"]),
        sa.ForeignKeyConstraint(["id_pessoa"], [f"{ESQUEMA}.pessoa.id_pessoa"]),
        sa.PrimaryKeyConstraint("id_procedimento"),
        schema=ESQUEMA,
    )
    for nome, colunas in (
        ("ix_procedimento_pessoa", ["id_pessoa"]),
        ("ix_procedimento_atendimento", ["id_atendimento"]),
        ("ix_procedimento_nome", ["nome_procedimento"]),
    ):
        op.create_index(nome, "procedimento", colunas, schema=ESQUEMA)

    # pk substituta: id_exame repete 29.471 vezes (ADR-002)
    op.create_table(
        "exame",
        sa.Column("pk", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("id_exame", sa.Integer(), nullable=False),
        sa.Column("id_pessoa", sa.Integer(), nullable=False),
        sa.Column("id_conceito_exame", sa.Integer()),
        sa.Column("data", sa.Date()),
        sa.Column("data_hora", sa.DateTime()),
        sa.Column("hora", sa.Text()),
        sa.Column("id_conceito_tipo_exame", sa.Integer()),
        sa.Column("id_conceito_operador", sa.Integer()),
        # 100% NULL neste dataset (ADR-008)
        sa.Column("valor_numerico", sa.Numeric()),
        sa.Column("id_conceito_valor", sa.Integer()),
        sa.Column("id_conceito_unidade", sa.Integer()),
        sa.Column("limite_inferior", sa.Numeric()),
        sa.Column("limite_superior", sa.Numeric()),
        sa.Column("id_profissional", sa.Integer()),
        sa.Column("id_atendimento", sa.Integer()),
        sa.Column("id_detalhe_atendimento", sa.Integer()),
        sa.Column("codigo_origem_exame", sa.Text()),
        sa.Column("id_conceito_origem_exame", sa.Integer()),
        sa.Column("unidade", sa.Text()),
        sa.Column("valor_origem", sa.Text()),
        sa.Column("nome_exame", sa.Text()),
        sa.ForeignKeyConstraint(["id_atendimento"], [f"{ESQUEMA}.atendimento.id_atendimento"]),
        sa.ForeignKeyConstraint(["id_pessoa"], [f"{ESQUEMA}.pessoa.id_pessoa"]),
        sa.PrimaryKeyConstraint("pk"),
        schema=ESQUEMA,
    )
    for nome, colunas in (
        ("ix_exame_pessoa", ["id_pessoa"]),
        ("ix_exame_atendimento", ["id_atendimento"]),
        ("ix_exame_nome", ["nome_exame"]),
        ("ix_exame_data", ["data"]),
        ("ix_exame_id_origem", ["id_exame"]),
    ):
        op.create_index(nome, "exame", colunas, schema=ESQUEMA)

    # pk substituta: id_observacao repete 619 vezes (ADR-002)
    op.create_table(
        "observacao",
        sa.Column("pk", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("id_observacao", sa.Integer(), nullable=False),
        sa.Column("id_pessoa", sa.Integer(), nullable=False),
        sa.Column("id_conceito_observacao", sa.Integer()),
        sa.Column("data", sa.Date()),
        sa.Column("data_hora", sa.DateTime()),
        sa.Column("id_conceito_tipo_observacao", sa.Integer()),
        sa.Column("valor_numerico", sa.Numeric()),
        sa.Column("valor_texto", sa.Text()),
        sa.Column("id_conceito_valor", sa.Integer()),
        sa.Column("id_conceito_qualificador", sa.Integer()),
        sa.Column("id_conceito_unidade", sa.Integer()),
        sa.Column("id_profissional", sa.Integer()),
        sa.Column("id_atendimento", sa.Integer()),
        sa.Column("id_detalhe_atendimento", sa.Integer()),
        sa.Column("codigo_origem_observacao", sa.Text()),
        sa.Column("id_conceito_origem_observacao", sa.Integer()),
        sa.Column("unidade", sa.Text()),
        sa.Column("qualificador", sa.Text()),
        sa.Column("nome_observacao", sa.Text()),
        sa.ForeignKeyConstraint(["id_atendimento"], [f"{ESQUEMA}.atendimento.id_atendimento"]),
        sa.ForeignKeyConstraint(["id_pessoa"], [f"{ESQUEMA}.pessoa.id_pessoa"]),
        sa.PrimaryKeyConstraint("pk"),
        schema=ESQUEMA,
    )
    for nome, colunas in (
        ("ix_observacao_pessoa", ["id_pessoa"]),
        ("ix_observacao_nome", ["nome_observacao"]),
        ("ix_observacao_id_origem", ["id_observacao"]),
    ):
        op.create_index(nome, "observacao", colunas, schema=ESQUEMA)

    op.create_table(
        "periodo_condicao",
        sa.Column("id_periodo_condicao", sa.Integer(), nullable=False),
        sa.Column("id_pessoa", sa.Integer(), nullable=False),
        sa.Column("id_conceito_condicao", sa.Integer()),
        sa.Column("data_inicio", sa.Date()),
        sa.Column("data_fim", sa.Date()),
        sa.Column("contagem_ocorrencias", sa.Integer()),
        sa.ForeignKeyConstraint(["id_pessoa"], [f"{ESQUEMA}.pessoa.id_pessoa"]),
        sa.PrimaryKeyConstraint("id_periodo_condicao"),
        schema=ESQUEMA,
    )
    op.create_index("ix_periodo_cond_pessoa", "periodo_condicao", ["id_pessoa"], schema=ESQUEMA)

    op.create_table(
        "periodo_medicamento",
        sa.Column("id_periodo_medicamento", sa.Integer(), nullable=False),
        sa.Column("id_pessoa", sa.Integer(), nullable=False),
        sa.Column("id_conceito_medicamento", sa.Integer()),
        sa.Column("data_inicio", sa.Date()),
        sa.Column("data_fim", sa.Date()),
        sa.Column("contagem_exposicoes", sa.Integer()),
        sa.Column("dias_intervalo", sa.Integer()),
        sa.ForeignKeyConstraint(["id_pessoa"], [f"{ESQUEMA}.pessoa.id_pessoa"]),
        sa.PrimaryKeyConstraint("id_periodo_medicamento"),
        schema=ESQUEMA,
    )
    op.create_index("ix_periodo_med_pessoa", "periodo_medicamento", ["id_pessoa"], schema=ESQUEMA)

    op.create_table(
        "dicionario_conceitos",
        sa.Column("codigo_origem", sa.Text(), nullable=False),
        sa.Column("vocabulario", sa.Text()),
        sa.Column("nome_portugues", sa.Text()),
        sa.Column("dominios", sa.Text()),
        sa.Column("ocorrencias", sa.Integer()),
        sa.Column("observacao", sa.Text()),
        sa.PrimaryKeyConstraint("codigo_origem"),
        schema=ESQUEMA,
    )


def downgrade() -> None:
    for tabela in (
        "dicionario_conceitos",
        "periodo_medicamento",
        "periodo_condicao",
        "observacao",
        "exame",
        "procedimento",
        "exposicao_medicamento",
        "condicao",
        "periodo_observacao",
        "atendimento",
        "pessoa",
    ):
        op.drop_table(tabela, schema=ESQUEMA)
