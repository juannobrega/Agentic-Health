"""Esquemas de paciente (E1)."""
from datetime import date

from pydantic import BaseModel, ConfigDict, Field

from api.esquemas.comum import FiltroQualidade


class PacienteResumo(BaseModel):
    """Item de lista. Pacientes não têm nome (ADR-009)."""

    model_config = ConfigDict(from_attributes=True)

    id_pessoa: int
    codigo_origem_pessoa: str | None = Field(
        default=None, description="UUID do Synthea — identificador estável entre cargas"
    )
    sexo: str | None
    idade: int | None = Field(default=None, description="Calculada sobre a data atual")
    raca: str | None
    etnia: str | None

    @property
    def rotulo(self) -> str:
        """Rótulo de exibição. Não existe nome de paciente no OMOP (ADR-009)."""
        partes = [f"Paciente #{self.id_pessoa}"]
        if self.sexo and self.idade is not None:
            partes.append(f"{self.sexo}, {self.idade} anos")
        return " · ".join(partes)


class ContadoresPaciente(BaseModel):
    condicoes: int
    medicamentos: int = Field(
        description="Apenas medicamentos RxNorm válidos; os inconsistentes são "
        "excluídos (ADR-008)"
    )
    procedimentos: int
    exames: int = Field(description="Exames pedidos — sem resultados disponíveis")
    atendimentos: int
    alergias: int


class JanelaObservacao(BaseModel):
    data_inicio: date | None
    data_fim: date | None


class PacienteDetalhe(PacienteResumo):
    ano_nascimento: int | None
    sexo_descricao: str | None
    raca_descricao: str | None
    janela_observacao: JanelaObservacao | None = None
    contadores: ContadoresPaciente
    aviso: str | None = Field(
        default=None,
        description="Preenchido quando o ano de nascimento é implausível",
    )


class EventoTimeline(BaseModel):
    """Evento na linha do tempo unificada (HU-1.3)."""

    tipo: str = Field(description="condicao | medicamento | procedimento | exame")
    data: date | None
    nome: str | None
    id_atendimento: int | None
    codigo_origem: str | None
    pk: int = Field(description="Identificador do registro de origem")
    valor_disponivel: bool = Field(
        default=True,
        description="Falso nos exames: o dataset não traz resultados (ADR-008)",
    )


class ItemCondicao(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_condicao: int
    nome_condicao: str | None
    data_inicio: date | None
    data_fim: date | None
    id_atendimento: int | None
    codigo_origem_condicao: str | None


class ItemMedicamento(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    pk: int
    nome_medicamento: str | None
    data_inicio: date | None
    data_fim: date | None
    dias_fornecimento: int | None
    id_atendimento: int | None
    codigo_origem_medicamento: str | None


class ItemProcedimento(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_procedimento: int
    nome_procedimento: str | None
    data: date | None
    id_atendimento: int | None
    codigo_origem_procedimento: str | None


class ItemExame(BaseModel):
    """Exame pedido. O dataset não traz resultados (ADR-008)."""

    model_config = ConfigDict(from_attributes=True)

    pk: int
    nome_exame: str | None
    data: date | None
    id_atendimento: int | None
    codigo_origem_exame: str | None
    valor_numerico: None = Field(
        default=None,
        description="Sempre nulo: os resultados se perderam no ETL do Synthea. "
        "A UI deve exibir 'não disponível', nunca vazio (ADR-008).",
    )


class ItemAlergia(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    pk: int
    nome_observacao: str | None
    data: date | None


class ListaMedicamentos(BaseModel):
    """Lista de medicamentos com o filtro de qualidade declarado (ADR-008)."""

    itens: list[ItemMedicamento]
    total: int
    pagina: int
    por_pagina: int
    filtro_qualidade: FiltroQualidade
