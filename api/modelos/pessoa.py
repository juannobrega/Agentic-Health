"""Demografia dos pacientes."""
from datetime import date, datetime

from sqlalchemy import ForeignKey, Index, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.modelos.base import Base, Visao


class Pessoa(Base):
    __tablename__ = "pessoa"

    id_pessoa: Mapped[int] = mapped_column(Integer, primary_key=True)

    id_conceito_sexo: Mapped[int | None]
    ano_nascimento: Mapped[int | None]
    mes_nascimento: Mapped[int | None]
    dia_nascimento: Mapped[int | None]
    data_hora_nascimento: Mapped[datetime | None]
    id_conceito_raca: Mapped[int | None]
    id_conceito_etnia: Mapped[int | None]
    id_local: Mapped[int | None]
    id_profissional: Mapped[int | None]
    id_unidade_saude: Mapped[int | None]

    # UUID gerado pelo Synthea — identificador estável entre cargas (ADR-009)
    codigo_origem_pessoa: Mapped[str | None] = mapped_column(Text)
    sexo: Mapped[str | None] = mapped_column(Text)
    id_conceito_origem_sexo: Mapped[int | None]
    raca: Mapped[str | None] = mapped_column(Text)
    id_conceito_origem_raca: Mapped[int | None]
    etnia: Mapped[str | None] = mapped_column(Text)
    id_conceito_origem_etnia: Mapped[int | None]
    sexo_descricao: Mapped[str | None] = mapped_column(Text)
    raca_descricao: Mapped[str | None] = mapped_column(Text)

    # lazy="raise": acesso não carregado explicitamente levanta erro em vez de
    # emitir query extra — previne N+1 silencioso (ADR-006)
    atendimentos: Mapped[list["Atendimento"]] = relationship(  # noqa: F821
        back_populates="pessoa", lazy="raise"
    )
    condicoes: Mapped[list["Condicao"]] = relationship(  # noqa: F821
        back_populates="pessoa", lazy="raise"
    )


class PessoaValida(Base, Visao):
    """vw_pessoa_valida — exclui os 2 anos de nascimento impossíveis e calcula idade."""

    __tablename__ = "vw_pessoa_valida"

    id_pessoa: Mapped[int] = mapped_column(Integer, primary_key=True)
    codigo_origem_pessoa: Mapped[str | None] = mapped_column(Text)
    sexo: Mapped[str | None] = mapped_column(Text)
    raca: Mapped[str | None] = mapped_column(Text)
    etnia: Mapped[str | None] = mapped_column(Text)
    ano_nascimento: Mapped[int | None]
    data_hora_nascimento: Mapped[datetime | None]
    sexo_descricao: Mapped[str | None] = mapped_column(Text)
    raca_descricao: Mapped[str | None] = mapped_column(Text)
    idade: Mapped[int | None]


class PeriodoObservacao(Base):
    __tablename__ = "periodo_observacao"
    __table_args__ = (Index("ix_periodo_obs_pessoa", "id_pessoa"),)

    id_periodo_observacao: Mapped[int] = mapped_column(Integer, primary_key=True)
    id_pessoa: Mapped[int] = mapped_column(ForeignKey("pessoa.id_pessoa"))
    data_inicio_periodo: Mapped[date | None]
    data_fim_periodo: Mapped[date | None]
    id_conceito_tipo_periodo: Mapped[int | None]
