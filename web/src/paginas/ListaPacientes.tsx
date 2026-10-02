import { useQuery } from "@tanstack/react-query";
import { Link, useSearchParams } from "react-router-dom";

import { obter } from "../api/cliente";
import type { Pagina, PacienteResumo } from "../api/tipos-dominio";
import { Carregando, Erro, Paginacao, Vazio } from "../componentes/basicos";

export function ListaPacientes() {
  // filtros na URL: torna a view compartilhável e sobrevive ao reload (ADR-007)
  const [parametros, setParametros] = useSearchParams();

  const pagina = Number(parametros.get("pagina") ?? 1);
  const sexo = parametros.get("sexo") ?? "";
  const idadeMin = parametros.get("idade_min") ?? "";
  const idadeMax = parametros.get("idade_max") ?? "";
  const condicao = parametros.get("condicao") ?? "";

  function atualizar(chave: string, valor: string) {
    const proximos = new URLSearchParams(parametros);
    if (valor) proximos.set(chave, valor);
    else proximos.delete(chave);
    if (chave !== "pagina") proximos.delete("pagina");
    setParametros(proximos);
  }

  const { data, isLoading, error } = useQuery({
    queryKey: ["pacientes", pagina, sexo, idadeMin, idadeMax, condicao],
    queryFn: () =>
      obter<Pagina<PacienteResumo>>("/pacientes", {
        pagina,
        por_pagina: 25,
        sexo: sexo || undefined,
        idade_min: idadeMin || undefined,
        idade_max: idadeMax || undefined,
        condicao: condicao || undefined,
      }),
  });

  return (
    <>
      <h2>Pacientes</h2>
      <p className="subtitulo">
        Pacientes não têm nome: o OMOP CDM é desidentificado por especificação.
        A busca é por identificador.
      </p>

      <div className="painel filtros">
        <div className="campo">
          <label htmlFor="busca-id">Identificador</label>
          <input
            id="busca-id"
            placeholder="ID ou UUID"
            defaultValue={parametros.get("q") ?? ""}
            onBlur={(e) => atualizar("q", e.target.value)}
          />
        </div>
        <div className="campo">
          <label htmlFor="f-sexo">Sexo</label>
          <select id="f-sexo" value={sexo} onChange={(e) => atualizar("sexo", e.target.value)}>
            <option value="">todos</option>
            <option value="M">M</option>
            <option value="F">F</option>
          </select>
        </div>
        <div className="campo">
          <label htmlFor="f-min">Idade mín.</label>
          <input
            id="f-min"
            type="number"
            min={0}
            max={130}
            value={idadeMin}
            onChange={(e) => atualizar("idade_min", e.target.value)}
          />
        </div>
        <div className="campo">
          <label htmlFor="f-max">Idade máx.</label>
          <input
            id="f-max"
            type="number"
            min={0}
            max={130}
            value={idadeMax}
            onChange={(e) => atualizar("idade_max", e.target.value)}
          />
        </div>
        <div className="campo">
          <label htmlFor="f-cond">Condição</label>
          <input
            id="f-cond"
            placeholder="nome exato"
            defaultValue={condicao}
            onBlur={(e) => atualizar("condicao", e.target.value)}
          />
        </div>
      </div>

      {isLoading && <Carregando />}
      {error && <Erro mensagem={(error as Error).message} />}

      {data && data.total === 0 && <Vazio texto="Nenhum paciente atende aos filtros." />}

      {data && data.total > 0 && (
        <>
          <div className="painel rolagem">
            <table>
              <thead>
                <tr>
                  <th>Paciente</th>
                  <th>Sexo</th>
                  <th>Idade</th>
                  <th>Raça</th>
                  <th>Etnia</th>
                  <th>UUID</th>
                </tr>
              </thead>
              <tbody>
                {data.itens.map((p) => (
                  <tr key={p.id_pessoa}>
                    <td>
                      <Link to={`/pacientes/${p.id_pessoa}`}>Paciente #{p.id_pessoa}</Link>
                    </td>
                    <td>{p.sexo ?? "—"}</td>
                    <td>{p.idade ?? "—"}</td>
                    <td>{p.raca ?? "—"}</td>
                    <td>{p.etnia ?? "—"}</td>
                    <td style={{ fontSize: 11.5, color: "var(--texto-suave)" }}>
                      {p.codigo_origem_pessoa?.slice(0, 8)}…
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
            onMudar={(p) => atualizar("pagina", String(p))}
          />
        </>
      )}
    </>
  );
}
