import { useMemo } from "react";

import type { EventoTimeline } from "../api/tipos-dominio";
import { Indisponivel, dataBr } from "./basicos";

const ROTULOS: Record<string, string> = {
  condicao: "condição",
  medicamento: "medicamento",
  procedimento: "procedimento",
  exame: "exame",
};

/**
 * Linha do tempo agrupada por ano.
 *
 * A paginação acontece no servidor: um paciente chega a 2.486 exames, e
 * renderizar tudo de uma vez congela a aba (ADR-007).
 */
export function Timeline({ eventos }: { eventos: EventoTimeline[] }) {
  const grupos = useMemo(() => {
    const mapa = new Map<string, EventoTimeline[]>();
    for (const evento of eventos) {
      const ano = evento.data?.slice(0, 4) ?? "sem data";
      const lista = mapa.get(ano);
      if (lista) lista.push(evento);
      else mapa.set(ano, [evento]);
    }
    return [...mapa.entries()];
  }, [eventos]);

  return (
    <>
      {grupos.map(([ano, lista]) => {
        const porTipo = lista.reduce<Record<string, number>>((acumulado, evento) => {
          acumulado[evento.tipo] = (acumulado[evento.tipo] ?? 0) + 1;
          return acumulado;
        }, {});
        return (
          <section className="grupo-ano" key={ano}>
            <header>
              <h4>{ano}</h4>
              <span className="contagem">
                {Object.entries(porTipo)
                  .map(([tipo, n]) => `${n} ${ROTULOS[tipo] ?? tipo}`)
                  .join(" · ")}
              </span>
            </header>
            {lista.map((evento) => (
              <div className="evento" key={`${evento.tipo}-${evento.pk}`}>
                <time>{dataBr(evento.data)}</time>
                <span className={`marca ${evento.tipo}`}>{ROTULOS[evento.tipo]}</span>
                <span>
                  {evento.nome ?? "—"}
                  {/* exames não têm resultado neste dataset (ADR-008) */}
                  {!evento.valor_disponivel && (
                    <>
                      {" "}
                      <Indisponivel texto="sem resultado" />
                    </>
                  )}
                </span>
              </div>
            ))}
          </section>
        );
      })}
    </>
  );
}
