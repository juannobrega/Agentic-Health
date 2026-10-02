"""Esquemas compartilhados (ADR-004).

`esquemas/` é a forma da API; `modelos/` é a forma do banco. São separados de
propósito: a API expõe idade calculada, oculta colunas internas e marca campos
indisponíveis (ADR-006, ADR-008).
"""
from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class Pagina(BaseModel, Generic[T]):
    """Envelope de toda lista. Paginação é obrigatória (ADR-004)."""

    itens: list[T]
    total: int = Field(description="Total de registros que atendem aos filtros")
    pagina: int = Field(ge=1)
    # o teto por endpoint é validado no parâmetro da rota; aqui só garantimos
    # que a paginação é positiva
    por_pagina: int = Field(ge=1)

    @property
    def total_paginas(self) -> int:
        return (self.total + self.por_pagina - 1) // self.por_pagina


class FiltroQualidade(BaseModel):
    """Filtros de qualidade aplicados a uma resposta (ADR-008).

    A API declara o que foi filtrado para que a UI possa mostrá-lo, em vez de
    esconder a limitação do dataset.
    """

    descricao: str
    registros_excluidos: int = 0


class StatusSaude(BaseModel):
    status: str
    banco_conectado: bool
    detalhe: str | None = None


class ContagemTabela(BaseModel):
    tabela: str
    linhas: int
    esperado: int
    conforme: bool


class StatusDados(BaseModel):
    carregado: bool
    conforme: bool
    resumo: str
    tabelas: list[ContagemTabela]
