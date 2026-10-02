"""Esquemas de estatísticas, coortes e dicionário (E3, E4)."""
from pydantic import BaseModel, ConfigDict, Field

from api.esquemas.comum import FiltroQualidade
from api.esquemas.paciente import PacienteResumo


class FaixaEtaria(BaseModel):
    faixa: str
    pacientes: int


class ContagemRotulada(BaseModel):
    rotulo: str
    pacientes: int


class ResumoPopulacional(BaseModel):
    total_pacientes: int = Field(description="Exclui os 2 nascimentos implausíveis")
    por_sexo: list[ContagemRotulada]
    por_raca: list[ContagemRotulada]
    piramide_etaria: list[FaixaEtaria]
    atendimentos_por_tipo: list[ContagemRotulada]
    pacientes_multimorbidade: int = Field(
        description="Pacientes com 2 ou mais condições crônicas distintas"
    )
    janela_temporal: str
    aviso_representatividade: str


class ItemPrevalencia(BaseModel):
    nome: str
    ocorrencias: int = Field(description="Total de registros")
    pacientes: int = Field(
        description="Pacientes distintos afetados — é esta a base da prevalência"
    )
    percentual_pacientes: float


class ListaPrevalencia(BaseModel):
    itens: list[ItemPrevalencia]
    total: int
    denominador: int = Field(description="Pacientes considerados no cálculo")
    filtro_qualidade: FiltroQualidade | None = None


class CriteriosCoorte(BaseModel):
    """Critérios combináveis. Compostos via ORM, sem concatenação (ADR-006)."""

    condicoes: list[str] = Field(default_factory=list)
    condicoes_todas: bool = Field(
        default=False,
        description="Falso: paciente com QUALQUER condição da lista. "
        "Verdadeiro: paciente com TODAS elas.",
    )
    medicamentos: list[str] = Field(default_factory=list)
    sexo: str | None = None
    raca: str | None = None
    idade_min: int | None = Field(default=None, ge=0, le=130)
    idade_max: int | None = Field(default=None, ge=0, le=130)
    tipo_atendimento: str | None = None


class PreviaCoorte(BaseModel):
    total: int
    filtros_aplicados: list[str]


class ResultadoCoorte(BaseModel):
    total: int
    pagina: int
    por_pagina: int
    itens: list[PacienteResumo]
    filtros_aplicados: list[str] = Field(
        description="Inclui os filtros de qualidade, não só os critérios pedidos"
    )


class ItemDicionario(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    codigo_origem: str
    vocabulario: str | None
    nome_portugues: str | None
    dominios: str | None
    ocorrencias: int | None
    observacao: str | None = Field(
        default=None, description="Preenchido nos códigos afetados por bug de ETL"
    )


class ResultadoBusca(BaseModel):
    termo: str
    condicoes: list[str]
    medicamentos: list[str]
    procedimentos: list[str]
    exames: list[str]
    observacoes: list[str]
    truncado: bool = Field(
        default=False, description="Verdadeiro se algum domínio atingiu o limite"
    )


class Sugestao(BaseModel):
    nome: str
    ocorrencias: int
