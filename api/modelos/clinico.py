"""Domínios clínicos: condição, medicamento, procedimento, exame, observação.

ATENÇÃO — chave substituta (ADR-002, ADR-006):
    exame, exposicao_medicamento e observacao têm IDs ORIGINAIS DUPLICADOS no
    dataset Synthea (29.471, 7.899 e 619 repetidos, respectivamente), apontando
    para registros clínicos distintos.

    Nessas três, a primary key é `pk` — a chave substituta gerada na carga.
    O ID original é coluna indexada SEM unicidade. Declará-lo como primary_key
    faria o SQLAlchemy tratar linhas distintas como a mesma entidade.
"""
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import BigInteger, ForeignKey, Index, Integer, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.modelos.base import Base, Visao


class Condicao(Base):
    """Diagnósticos. id_condicao é único no dataset — PK natural."""

    __tablename__ = "condicao"
    __table_args__ = (
        Index("ix_condicao_pessoa", "id_pessoa"),
        Index("ix_condicao_atendimento", "id_atendimento"),
        Index("ix_condicao_conceito", "id_conceito_condicao"),
        Index("ix_condicao_nome", "nome_condicao"),
        Index("ix_condicao_data", "data_inicio"),
    )

    id_condicao: Mapped[int] = mapped_column(Integer, primary_key=True)
    id_pessoa: Mapped[int] = mapped_column(ForeignKey("pessoa.id_pessoa"))
    id_atendimento: Mapped[int | None] = mapped_column(
        ForeignKey("atendimento.id_atendimento")
    )

    id_conceito_condicao: Mapped[int | None]
    data_inicio: Mapped[date | None]
    data_hora_inicio: Mapped[datetime | None]
    data_fim: Mapped[date | None]
    data_hora_fim: Mapped[datetime | None]
    id_conceito_tipo_condicao: Mapped[int | None]
    motivo_interrupcao: Mapped[str | None] = mapped_column(Text)
    id_profissional: Mapped[int | None]
    id_detalhe_atendimento: Mapped[int | None]
    codigo_origem_condicao: Mapped[str | None] = mapped_column(Text)
    id_conceito_origem_condicao: Mapped[int | None]
    situacao_condicao: Mapped[str | None] = mapped_column(Text)
    id_conceito_situacao: Mapped[int | None]

    # nome clínico em português, resolvido do código SNOMED (ADR-001)
    nome_condicao: Mapped[str | None] = mapped_column(Text)

    pessoa: Mapped["Pessoa"] = relationship(  # noqa: F821
        back_populates="condicoes", lazy="raise"
    )
    atendimento: Mapped["Atendimento | None"] = relationship(
        back_populates="condicoes", lazy="raise"
    )


class Procedimento(Base):
    """Procedimentos. id_procedimento é único no dataset — PK natural."""

    __tablename__ = "procedimento"
    __table_args__ = (
        Index("ix_procedimento_pessoa", "id_pessoa"),
        Index("ix_procedimento_atendimento", "id_atendimento"),
        Index("ix_procedimento_nome", "nome_procedimento"),
    )

    id_procedimento: Mapped[int] = mapped_column(Integer, primary_key=True)
    id_pessoa: Mapped[int] = mapped_column(ForeignKey("pessoa.id_pessoa"))
    id_atendimento: Mapped[int | None] = mapped_column(
        ForeignKey("atendimento.id_atendimento")
    )

    id_conceito_procedimento: Mapped[int | None]
    data: Mapped[date | None]
    data_hora: Mapped[datetime | None]
    id_conceito_tipo_procedimento: Mapped[int | None]
    id_conceito_modificador: Mapped[int | None]
    quantidade: Mapped[Decimal | None]
    id_profissional: Mapped[int | None]
    id_detalhe_atendimento: Mapped[int | None]
    codigo_origem_procedimento: Mapped[str | None] = mapped_column(Text)
    id_conceito_origem_procedimento: Mapped[int | None]
    modificador: Mapped[str | None] = mapped_column(Text)
    nome_procedimento: Mapped[str | None] = mapped_column(Text)

    atendimento: Mapped["Atendimento | None"] = relationship(
        back_populates="procedimentos", lazy="raise"
    )


class ExposicaoMedicamento(Base):
    """Prescrições.

    PK é `pk` — id_exposicao_medicamento tem 7.899 valores repetidos.

    NÃO CONSULTE ESTA TABELA para listar medicamentos: 26,8% das linhas trazem
    código SNOMED de condição em vez de RxNorm (ADR-008). Use MedicamentoValido.
    """

    __tablename__ = "exposicao_medicamento"
    __table_args__ = (
        Index("ix_medicamento_pessoa", "id_pessoa"),
        Index("ix_medicamento_atendimento", "id_atendimento"),
        Index("ix_medicamento_nome", "nome_medicamento"),
        Index("ix_medicamento_id_origem", "id_exposicao_medicamento"),
        # índice parcial: consultas de medicamento quase sempre filtram as
        # linhas com bug de ETL (ADR-008)
        Index(
            "ix_medicamento_validos",
            "id_pessoa",
            postgresql_where=text("inconsistencia_vocabulario IS NULL"),
        ),
    )

    pk: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    # NÃO é único — 7.899 repetidos
    id_exposicao_medicamento: Mapped[int] = mapped_column(Integer)

    id_pessoa: Mapped[int] = mapped_column(ForeignKey("pessoa.id_pessoa"))
    id_atendimento: Mapped[int | None] = mapped_column(
        ForeignKey("atendimento.id_atendimento")
    )

    id_conceito_medicamento: Mapped[int | None]
    data_inicio: Mapped[date | None]
    data_hora_inicio: Mapped[datetime | None]
    data_fim: Mapped[date | None]
    data_hora_fim: Mapped[datetime | None]
    data_fim_literal: Mapped[date | None]
    id_conceito_tipo_medicamento: Mapped[int | None]
    motivo_interrupcao: Mapped[str | None] = mapped_column(Text)
    reposicoes: Mapped[int | None]
    quantidade: Mapped[Decimal | None]
    dias_fornecimento: Mapped[int | None]
    posologia: Mapped[str | None] = mapped_column(Text)
    id_conceito_via: Mapped[int | None]
    numero_lote: Mapped[str | None] = mapped_column(Text)
    id_profissional: Mapped[int | None]
    id_detalhe_atendimento: Mapped[int | None]
    codigo_origem_medicamento: Mapped[str | None] = mapped_column(Text)
    id_conceito_origem_medicamento: Mapped[int | None]
    via_administracao: Mapped[str | None] = mapped_column(Text)
    unidade_dose: Mapped[str | None] = mapped_column(Text)
    nome_medicamento: Mapped[str | None] = mapped_column(Text)

    # 'codigo_de_condicao' nas 7.899 linhas afetadas; NULL nas válidas (ADR-008)
    inconsistencia_vocabulario: Mapped[str | None] = mapped_column(Text)


class MedicamentoValido(Base, Visao):
    """vw_medicamento_valido — os 21.619 medicamentos RxNorm reais.

    É esta a entidade a usar para qualquer consulta de medicamento (ADR-008).
    """

    __tablename__ = "vw_medicamento_valido"

    pk: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    id_exposicao_medicamento: Mapped[int]
    id_pessoa: Mapped[int]
    id_atendimento: Mapped[int | None]
    id_conceito_medicamento: Mapped[int | None]
    data_inicio: Mapped[date | None]
    data_hora_inicio: Mapped[datetime | None]
    data_fim: Mapped[date | None]
    data_hora_fim: Mapped[datetime | None]
    data_fim_literal: Mapped[date | None]
    id_conceito_tipo_medicamento: Mapped[int | None]
    motivo_interrupcao: Mapped[str | None] = mapped_column(Text)
    reposicoes: Mapped[int | None]
    quantidade: Mapped[Decimal | None]
    dias_fornecimento: Mapped[int | None]
    posologia: Mapped[str | None] = mapped_column(Text)
    id_conceito_via: Mapped[int | None]
    numero_lote: Mapped[str | None] = mapped_column(Text)
    id_profissional: Mapped[int | None]
    id_detalhe_atendimento: Mapped[int | None]
    codigo_origem_medicamento: Mapped[str | None] = mapped_column(Text)
    id_conceito_origem_medicamento: Mapped[int | None]
    via_administracao: Mapped[str | None] = mapped_column(Text)
    unidade_dose: Mapped[str | None] = mapped_column(Text)
    nome_medicamento: Mapped[str | None] = mapped_column(Text)
    inconsistencia_vocabulario: Mapped[str | None] = mapped_column(Text)


class Exame(Base):
    """Exames e sinais vitais.

    PK é `pk` — id_exame tem 29.471 valores repetidos.

    valor_numerico é SEMPRE NULL neste dataset: os resultados se perderam no ETL
    do Synthea (ADR-008). A tabela indica apenas QUAL exame foi pedido e QUANDO.
    """

    __tablename__ = "exame"
    __table_args__ = (
        Index("ix_exame_pessoa", "id_pessoa"),
        Index("ix_exame_atendimento", "id_atendimento"),
        Index("ix_exame_nome", "nome_exame"),
        Index("ix_exame_data", "data"),
        Index("ix_exame_id_origem", "id_exame"),
    )

    pk: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    # NÃO é único — 29.471 repetidos
    id_exame: Mapped[int] = mapped_column(Integer)

    id_pessoa: Mapped[int] = mapped_column(ForeignKey("pessoa.id_pessoa"))
    id_atendimento: Mapped[int | None] = mapped_column(
        ForeignKey("atendimento.id_atendimento")
    )

    id_conceito_exame: Mapped[int | None]
    data: Mapped[date | None]
    data_hora: Mapped[datetime | None]
    hora: Mapped[str | None] = mapped_column(Text)
    id_conceito_tipo_exame: Mapped[int | None]
    id_conceito_operador: Mapped[int | None]

    # 100% NULL no dataset (ADR-008)
    valor_numerico: Mapped[Decimal | None]
    id_conceito_valor: Mapped[int | None]
    id_conceito_unidade: Mapped[int | None]
    limite_inferior: Mapped[Decimal | None]
    limite_superior: Mapped[Decimal | None]

    id_profissional: Mapped[int | None]
    id_detalhe_atendimento: Mapped[int | None]
    codigo_origem_exame: Mapped[str | None] = mapped_column(Text)
    id_conceito_origem_exame: Mapped[int | None]
    unidade: Mapped[str | None] = mapped_column(Text)
    valor_origem: Mapped[str | None] = mapped_column(Text)
    nome_exame: Mapped[str | None] = mapped_column(Text)


class Observacao(Base):
    """Observações clínicas, incluindo as 619 alergias.

    PK é `pk` — id_observacao tem 619 valores repetidos.

    83% das linhas têm id_conceito_observacao = 0 (não mapeado no OMOP): filtre
    por nome_observacao, não por conceito (ADR-001).
    """

    __tablename__ = "observacao"
    __table_args__ = (
        Index("ix_observacao_pessoa", "id_pessoa"),
        Index("ix_observacao_nome", "nome_observacao"),
        Index("ix_observacao_id_origem", "id_observacao"),
    )

    pk: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    # NÃO é único — 619 repetidos
    id_observacao: Mapped[int] = mapped_column(Integer)

    id_pessoa: Mapped[int] = mapped_column(ForeignKey("pessoa.id_pessoa"))
    id_atendimento: Mapped[int | None] = mapped_column(
        ForeignKey("atendimento.id_atendimento")
    )

    id_conceito_observacao: Mapped[int | None]
    data: Mapped[date | None]
    data_hora: Mapped[datetime | None]
    id_conceito_tipo_observacao: Mapped[int | None]
    valor_numerico: Mapped[Decimal | None]
    valor_texto: Mapped[str | None] = mapped_column(Text)
    id_conceito_valor: Mapped[int | None]
    id_conceito_qualificador: Mapped[int | None]
    id_conceito_unidade: Mapped[int | None]
    id_profissional: Mapped[int | None]
    id_detalhe_atendimento: Mapped[int | None]
    codigo_origem_observacao: Mapped[str | None] = mapped_column(Text)
    id_conceito_origem_observacao: Mapped[int | None]
    unidade: Mapped[str | None] = mapped_column(Text)
    qualificador: Mapped[str | None] = mapped_column(Text)
    nome_observacao: Mapped[str | None] = mapped_column(Text)


class PeriodoCondicao(Base):
    __tablename__ = "periodo_condicao"
    __table_args__ = (Index("ix_periodo_cond_pessoa", "id_pessoa"),)

    id_periodo_condicao: Mapped[int] = mapped_column(Integer, primary_key=True)
    id_pessoa: Mapped[int] = mapped_column(ForeignKey("pessoa.id_pessoa"))
    id_conceito_condicao: Mapped[int | None]
    data_inicio: Mapped[date | None]
    data_fim: Mapped[date | None]
    contagem_ocorrencias: Mapped[int | None]


class PeriodoMedicamento(Base):
    __tablename__ = "periodo_medicamento"
    __table_args__ = (Index("ix_periodo_med_pessoa", "id_pessoa"),)

    id_periodo_medicamento: Mapped[int] = mapped_column(Integer, primary_key=True)
    id_pessoa: Mapped[int] = mapped_column(ForeignKey("pessoa.id_pessoa"))
    id_conceito_medicamento: Mapped[int | None]
    data_inicio: Mapped[date | None]
    data_fim: Mapped[date | None]
    contagem_exposicoes: Mapped[int | None]
    dias_intervalo: Mapped[int | None]


class DicionarioConceito(Base):
    """De-para dos 535 códigos clínicos para português (ADR-001)."""

    __tablename__ = "dicionario_conceitos"

    codigo_origem: Mapped[str] = mapped_column(Text, primary_key=True)
    vocabulario: Mapped[str | None] = mapped_column(Text)
    nome_portugues: Mapped[str | None] = mapped_column(Text)
    dominios: Mapped[str | None] = mapped_column(Text)
    ocorrencias: Mapped[int | None]
    observacao: Mapped[str | None] = mapped_column(Text)
