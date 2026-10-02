import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router-dom";

import { obter } from "../api/cliente";
import type { AtendimentoResumo, Pagina } from "../api/tipos-dominio";
import { Carregando, Erro, Paginacao, Vazio, dataBr } from "../componentes/basicos";

const TIPOS = ["Ambulatorial", "Emergência", "Internação"];

export function Atendimentos() {
  const [pagina, setPagina] = useState(1);
  const [tipo, setTipo] = useState("");

  const { data, isLoading, error } = useQuery({
    queryKey: ["atendimentos", pagina, tipo],
    queryFn: () =>
      obter<Pagina<AtendimentoResumo>>("/atendimentos", {
        pagina,
        por_pagina: 25,
        tipo: tipo || undefined,
      }),
  });

  return (
    <>
      <h2>Atendimentos</h2>
      <p className="subtitulo">Cobertura: 1909 a janeiro de 2019.</p>

      <div className="chips" style={{ marginBottom: 16 }}>
        <button
          className={`chip ${tipo === "" ? "ativo" : ""}`}
          onClick={() => {
            setTipo("");
            setPagina(1);
          }}
        >
          todos
        </button>
        {TIPOS.map((t) => (
          <button
            key={t}
            className={`chip ${tipo === t ? "ativo" : ""}`}
            onClick={() => {
              setTipo(t);
              setPagina(1);
            }}
          >
            {t}
          </button>
        ))}
      </div>

      {isLoading && <Carregando />}
      {error && <Erro mensagem={(error as Error).message} />}
      {data && data.total === 0 && <Vazio texto="Nenhum atendimento encontrado." />}

      {data && data.total > 0 && (
        <>
          <div className="painel rolagem">
            <table>
              <thead>
                <tr>
                  <th>Atendimento</th>
                  <th>Tipo</th>
                  <th>Início</th>
                  <th>Duração</th>
                  <th>Paciente</th>
                </tr>
              </thead>
              <tbody>
                {data.itens.map((a) => (
                  <tr key={a.id_atendimento}>
                    <td>
                      <Link to={`/atendimentos/${a.id_atendimento}`}>#{a.id_atendimento}</Link>
                    </td>
                    <td>{a.tipo ?? "—"}</td>
                    <td>{dataBr(a.data_inicio)}</td>
                    <td>{a.duracao_dias !== null ? `${a.duracao_dias}d` : "—"}</td>
                    <td>
                      <Link to={`/pacientes/${a.id_pessoa}`}>#{a.id_pessoa}</Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <Paginacao
            pagina={data.pagina}
            porPagina={data.por_pagina}
            total={data.total}
            onMudar={setPagina}
          />
        </>
      )}
    </>
  );
}
