/**
 * Garante que os tipos de domínio escritos à mão concordam com o contrato
 * GERADO do OpenAPI (src/api/tipos.ts).
 *
 * Este arquivo não produz código: existe para o `tsc` falhar se o backend
 * mudar um campo e os tipos do frontend ficarem defasados (ADR-007).
 */
import type { components } from "./tipos";
import type {
  AtendimentoDetalhe,
  EventoTimeline,
  ItemExame,
  ListaMedicamentos,
  PacienteDetalhe,
  ResumoPopulacional,
  Trajetoria,
} from "./tipos-dominio";

type Esquemas = components["schemas"];

/** Falha a compilação se `Manual` não for compatível com `Gerado`. */
type Confere<Gerado, Manual extends Gerado> = Manual;

export type _Paciente = Confere<Esquemas["PacienteDetalhe"], PacienteDetalhe>;
export type _Evento = Confere<Esquemas["EventoTimeline"], EventoTimeline>;
export type _Exame = Confere<Esquemas["ItemExame"], ItemExame>;
export type _Medicamentos = Confere<Esquemas["ListaMedicamentos"], ListaMedicamentos>;
export type _Atendimento = Confere<Esquemas["AtendimentoDetalhe"], AtendimentoDetalhe>;
export type _Trajetoria = Confere<Esquemas["Trajetoria"], Trajetoria>;
export type _Resumo = Confere<Esquemas["ResumoPopulacional"], ResumoPopulacional>;
