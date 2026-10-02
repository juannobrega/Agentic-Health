"""Atendimentos (visitas)."""
from datetime import date, datetime

from sqlalchemy import ForeignKey, Index, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.modelos.base import Base, Visao


class Atendimento(Base):
    __tablename__ = "atendimento"
    __table_args__ = (
        Index("ix_atendimento_pessoa", "id_pessoa"),
        Index("ix_atendimento_data", "data_inicio"),
    )

    id_atendimento: Mapped[int] = mapped_column(Integer, primary_key=True)
    id_pessoa: Mapped[int] = mapped_column(ForeignKey("pessoa.id_pessoa"))

    id_conceito_atendimento: Mapped[int | None]
    data_inicio: Mapped[date | None]
    data_hora_inicio: Mapped[datetime | None]
    data_fim: Mapped[date | None]
    data_hora_fim: Mapped[datetime | None]
    id_conceito_tipo_atendimento: Mapped[int | None]
    id_profissional: Mapped[int | None]
    id_unidade_saude: Mapped[int | None]
    codigo_origem_atendimento: Mapped[str | None] = mapped_column(Text)
    id_conceito_origem_atendimento: Mapped[int | None]
    id_conceito_origem_admissao: Mapped[int | None]
    origem_admissao: Mapped[str | None] = mapped_column(Text)
    id_conceito_destino_alta: Mapped[int | None]
    destino_alta: Mapped[str | None] = mapped_column(Text)

    # encadeamento usado pela trajetória — 31.027 atendimentos têm predecessor
    id_atendimento_anterior: Mapped[int | None]

    # Ambulatorial / Emergência / Internação
    atendimento_descricao: Mapped[str | None] = mapped_column(Text)

    pessoa: Mapped["Pessoa"] = relationship(  # noqa: F821
        back_populates="atendimentos", lazy="raise"
    )
    condicoes: Mapped[list["Condicao"]] = relationship(  # noqa: F821
        back_populates="atendimento", lazy="raise"
    )
    procedimentos: Mapped[list["Procedimento"]] = relationship(  # noqa: F821
        back_populates="atendimento", lazy="raise"
    )


class AtendimentoResumo(Base, Visao):
    """vw_atendimento_resumo — um atendimento por linha com contadores."""

    __tablename__ = "vw_atendimento_resumo"

    id_atendimento: Mapped[int] = mapped_column(Integer, primary_key=True)
    id_pessoa: Mapped[int]
    sexo: Mapped[str | None] = mapped_column(Text)
    raca: Mapped[str | None] = mapped_column(Text)
    data_inicio: Mapped[date | None]
    atendimento_descricao: Mapped[str | None] = mapped_column(Text)
    qtd_condicoes: Mapped[int | None]
    qtd_procedimentos: Mapped[int | None]
    qtd_exames: Mapped[int | None]
    qtd_medicamentos: Mapped[int | None]
