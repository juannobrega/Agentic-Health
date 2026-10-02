import type { ReactNode } from "react";

import type { FiltroQualidade } from "../api/tipos-dominio";

export function Carregando({ texto = "Carregando…" }: { texto?: string }) {
  return <div className="estado">{texto}</div>;
}

export function Erro({ mensagem }: { mensagem: string }) {
  return (
    <div className="alerta">
      <strong>Não foi possível carregar</strong>
      {mensagem}
    </div>
  );
}

export function Vazio({ texto }: { texto: string }) {
  return <div className="estado">{texto}</div>;
}

/**
 * Valor que o dataset não fornece.
 *
 * Renderizar string vazia faria parecer defeito de software; "não disponível"
 * diz que o sistema funciona e o dado não existe (ADR-008).
 */
export function Indisponivel({ texto = "não disponível" }: { texto?: string }) {
  return <span className="indisponivel">{texto}</span>;
}

/** Avisa sobre um filtro de qualidade aplicado, em vez de filtrar em silêncio. */
export function AvisoQualidade({ filtro }: { filtro: FiltroQualidade | null }) {
  if (!filtro) return null;
  const sufixo =
    filtro.registros_excluidos > 0
      ? ` ${filtro.registros_excluidos} registro(s) excluído(s).`
      : "";
  return (
    <div className="aviso">
      {filtro.descricao}
      {sufixo}
    </div>
  );
}

export function Cartao({ valor, rotulo }: { valor: ReactNode; rotulo: string }) {
  return (
    <div className="cartao">
      <div className="valor">{valor}</div>
      <div className="rotulo">{rotulo}</div>
    </div>
  );
}

export function Paginacao({
  pagina,
  porPagina,
  total,
  onMudar,
}: {
  pagina: number;
  porPagina: number;
  total: number;
  onMudar: (pagina: number) => void;
}) {
  const ultima = Math.max(1, Math.ceil(total / porPagina));
  if (total === 0) return null;
  const inicio = (pagina - 1) * porPagina + 1;
  const fim = Math.min(pagina * porPagina, total);
  return (
    <div className="paginacao">
      <button onClick={() => onMudar(pagina - 1)} disabled={pagina <= 1}>
        anterior
      </button>
      <span>
        {inicio}–{fim} de {total.toLocaleString("pt-BR")}
      </span>
      <button onClick={() => onMudar(pagina + 1)} disabled={pagina >= ultima}>
        próxima
      </button>
    </div>
  );
}

export function dataBr(valor: string | null | undefined): string {
  if (!valor) return "—";
  const [ano, mes, dia] = valor.split("-");
  return `${dia}/${mes}/${ano}`;
}

export function Barra({ percentual }: { percentual: number }) {
  return (
    <div className="barra">
      <span style={{ width: `${Math.min(100, percentual)}%` }} />
    </div>
  );
}
