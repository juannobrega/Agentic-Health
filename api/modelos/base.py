"""Base declarativa do SQLAlchemy (ADR-006)."""
from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

from api.config import obter_configuracao

_cfg = obter_configuracao()


class Base(DeclarativeBase):
    """Todas as tabelas vivem no schema de dados (ADR-002)."""

    metadata = MetaData(schema=_cfg.schema_dados)


class Visao:
    """Marca um modelo como view, não tabela.

    O autogenerate do Alembic precisa ignorá-los, senão tenta criar as views
    como tabela (ADR-006).
    """

    __abstract__ = True
    _e_visao = True
