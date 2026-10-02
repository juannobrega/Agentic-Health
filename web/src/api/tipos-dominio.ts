/**
 * Tipos de domínio escritos à mão.
 *
 * `tipos.ts` é GERADO do OpenAPI (npm run tipos) e é a fonte de verdade do
 * contrato. Estes aliases dão nomes curtos ao que as telas usam, e existem
 * separados para que a geração possa sobrescrever tipos.ts sem conflito.
 */

export interface Pagina<T> {
  itens: T[];
  total: number;
  pagina: number;
  por_pagina: number;
}

export interface PacienteResumo {
  id_pessoa: number;
  codigo_origem_pessoa: string | null;
  sexo: string | null;
  idade: number | null;
  raca: string | null;
  etnia: string | null;
}

export interface ContadoresPaciente {
  condicoes: number;
  medicamentos: number;
  procedimentos: number;
  exames: number;
  atendimentos: number;
  alergias: number;
}

export interface PacienteDetalhe extends PacienteResumo {
  ano_nascimento: number | null;
  sexo_descricao: string | null;
  raca_descricao: string | null;
  janela_observacao: { data_inicio: string | null; data_fim: string | null } | null;
  contadores: ContadoresPaciente;
  aviso: string | null;
}

export type TipoEvento = "condicao" | "medicamento" | "procedimento" | "exame";

export interface EventoTimeline {
  tipo: TipoEvento;
  data: string | null;
  nome: string | null;
  id_atendimento: number | null;
  codigo_origem: string | null;
  pk: number;
  /** Falso nos exames: o dataset não traz resultados (ADR-008) */
  valor_disponivel: boolean;
}

export interface FiltroQualidade {
  descricao: string;
  registros_excluidos: number;
}

export interface ItemCondicao {
  id_condicao: number;
  nome_condicao: string | null;
  data_inicio: string | null;
  data_fim: string | null;
  id_atendimento: number | null;
  codigo_origem_condicao: string | null;
}

export interface ItemMedicamento {
  pk: number;
  nome_medicamento: string | null;
  data_inicio: string | null;
  data_fim: string | null;
  dias_fornecimento: number | null;
  id_atendimento: number | null;
  codigo_origem_medicamento: string | null;
}

export interface ItemProcedimento {
  id_procedimento: number;
  nome_procedimento: string | null;
  data: string | null;
  id_atendimento: number | null;
  codigo_origem_procedimento: string | null;
}

export interface ItemExame {
  pk: number;
  nome_exame: string | null;
  data: string | null;
  id_atendimento: number | null;
  codigo_origem_exame: string | null;
  /** Sempre nulo neste dataset (ADR-008) */
  valor_numerico?: null;
}

export interface ItemAlergia {
  pk: number;
  nome_observacao: string | null;
  data: string | null;
}

export interface ListaMedicamentos {
  itens: ItemMedicamento[];
  total: number;
  pagina: number;
  por_pagina: number;
  filtro_qualidade: FiltroQualidade;
}

export interface ContagemRotulada {
  rotulo: string;
  pacientes: number;
}

export interface ResumoPopulacional {
  total_pacientes: number;
  por_sexo: ContagemRotulada[];
  por_raca: ContagemRotulada[];
  piramide_etaria: { faixa: string; pacientes: number }[];
  atendimentos_por_tipo: ContagemRotulada[];
  pacientes_multimorbidade: number;
  janela_temporal: string;
  aviso_representatividade: string;
}

export interface ItemPrevalencia {
  nome: string;
  ocorrencias: number;
  pacientes: number;
  percentual_pacientes: number;
}

export interface ListaPrevalencia {
  itens: ItemPrevalencia[];
  total: number;
  denominador: number;
  filtro_qualidade: FiltroQualidade | null;
}

export interface AtendimentoResumo {
  id_atendimento: number;
  id_pessoa: number;
  tipo: string | null;
  data_inicio: string | null;
  data_fim: string | null;
  duracao_dias: number | null;
}

export interface AtendimentoDetalhe extends AtendimentoResumo {
  sexo: string | null;
  idade: number | null;
  id_atendimento_anterior: number | null;
  condicoes: ItemCondicao[];
  medicamentos: ItemMedicamento[];
  procedimentos: ItemProcedimento[];
  exames: ItemExame[];
}

export interface PassoTrajetoria {
  ordem: number;
  id_atendimento: number;
  tipo: string | null;
  data_inicio: string | null;
  dias_desde_anterior: number | null;
  condicoes: string[];
}

export interface Trajetoria {
  id_pessoa: number;
  total_atendimentos: number;
  passos: PassoTrajetoria[];
  truncada: boolean;
  ciclo_detectado: boolean;
}

export interface CriteriosCoorte {
  condicoes?: string[];
  condicoes_todas?: boolean;
  medicamentos?: string[];
  sexo?: string | null;
  raca?: string | null;
  idade_min?: number | null;
  idade_max?: number | null;
  tipo_atendimento?: string | null;
}

export interface ResultadoCoorte {
  total: number;
  pagina: number;
  por_pagina: number;
  itens: PacienteResumo[];
  filtros_aplicados: string[];
}

export interface PreviaCoorte {
  total: number;
  filtros_aplicados: string[];
}

export interface ResultadoBusca {
  termo: string;
  condicoes: string[];
  medicamentos: string[];
  procedimentos: string[];
  exames: string[];
  observacoes: string[];
  truncado: boolean;
}

export interface Sugestao {
  nome: string;
  ocorrencias: number;
}

/** Rótulo de exibição. Pacientes não têm nome no OMOP (ADR-009). */
export function rotuloPaciente(p: Pick<PacienteResumo, "id_pessoa" | "sexo" | "idade">): string {
  const base = `Paciente #${p.id_pessoa}`;
  if (p.sexo && p.idade !== null) return `${base} · ${p.sexo}, ${p.idade} anos`;
  return base;
}
