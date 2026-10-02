"""Esquemas de atendimento e trajetória (E2)."""
from datetime import date

from pydantic import BaseModel, ConfigDict, Field

from api.esquemas.paciente import (
    ItemCondicao,
    ItemExame,
    ItemMedicamento,
    ItemProcedimento,
)

TIPOS_ATENDIMENTO = ("Ambulatorial", "Emergência", "Internação")


class AtendimentoResumo(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_atendimento: int
    id_pessoa: int
    tipo: str | None = Field(default=None, description="Ambulatorial, Emergência ou Internação")
    data_inicio: date | None
    data_fim: date | None
    duracao_dias: int | None = Field(default=None, description="Dias entre início e fim")


class AtendimentoDetalhe(AtendimentoResumo):
    """Tudo que aconteceu no atendimento."""

    sexo: str | None = None
    idade: int | None = None
    id_atendimento_anterior: int | None = None
    condicoes: list[ItemCondicao]
    medicamentos: list[ItemMedicamento] = Field(
        description="Apenas medicamentos RxNorm válidos (ADR-008)"
    )
    procedimentos: list[ItemProcedimento]
    exames: list[ItemExame] = Field(
        description="Exames pedidos — o dataset não traz resultados (ADR-008)"
    )


class PassoTrajetoria(BaseModel):
    """Um atendimento na sequência encadeada."""

    ordem: int
    id_atendimento: int
    tipo: str | None
    data_inicio: date | None
    dias_desde_anterior: int | None
    condicoes: list[str]


class Trajetoria(BaseModel):
    id_pessoa: int
    total_atendimentos: int
    passos: list[PassoTrajetoria]
    truncada: bool = Field(
        default=False, description="Verdadeiro se o limite de passos foi atingido"
    )
    ciclo_detectado: bool = Field(
        default=False,
        description="Verdadeiro se a cadeia revisita um atendimento — nada no "
        "dataset garante ausência de ciclo",
    )


class ItemReinternacao(BaseModel):
    id_pessoa: int
    sexo: str | None
    idade: int | None
    internacoes: int
    menor_intervalo_dias: int | None
    maior_intervalo_dias: int | None
