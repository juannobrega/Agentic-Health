import { useMutation, useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { enviar, obter } from "../api/cliente";
import type {
  CriteriosCoorte,
  PreviaCoorte,
  ResultadoCoorte,
  Sugestao,
} from "../api/tipos-dominio";
import { Carregando, Erro, Vazio } from "../componentes/basicos";

export function Coortes() {
  const [condicoes, setCondicoes] = useState<string[]>([]);
  const [todas, setTodas] = useState(false);
  const [sexo, setSexo] = useState("");
  const [idadeMin, setIdadeMin] = useState("");
  const [idadeMax, setIdadeMax] = useState("");
  const [termo, setTermo] = useState("");
  const [termoAtrasado, setTermoAtrasado] = useState("");
  const [resultado, setResultado] = useState<ResultadoCoorte | null>(null);

  // debounce: evita um request por tecla digitada
  useEffect(() => {
    const id = setTimeout(() => setTermoAtrasado(termo), 300);
    return () => clearTimeout(id);
  }, [termo]);

  const criterios: CriteriosCoorte = {
    condicoes,
    condicoes_todas: todas,
    sexo: sexo || null,
    idade_min: idadeMin ? Number(idadeMin) : null,
    idade_max: idadeMax ? Number(idadeMax) : null,
  };

  const sugestoes = useQuery({
    queryKey: ["sugestoes", termoAtrasado],
    queryFn: () =>
      obter<Sugestao[]>("/dicionario/sugestoes", {
        q: termoAtrasado,
        dominio: "condicoes",
      }),
    enabled: termoAtrasado.length >= 2,
  });

  // prévia recalculada a cada mudança de critério (HU-3.3)
  const previa = useQuery({
    queryKey: ["previa", criterios],
    queryFn: () => enviar<PreviaCoorte>("/coortes/previa", criterios),
  });

  const montar = useMutation({
    mutationFn: () => enviar<ResultadoCoorte>("/coortes", criterios, { por_pagina: 50 }),
    onSuccess: setResultado,
  });

  function alternarCondicao(nome: string) {
    setCondicoes((atual) =>
      atual.includes(nome) ? atual.filter((c) => c !== nome) : [...atual, nome],
    );
    setResultado(null);
  }

  return (
    <>
      <h2>Construtor de coortes</h2>
      <p className="subtitulo">
        O N é recalculado a cada critério. Os filtros de qualidade aplicados
        aparecem junto do resultado.
      </p>

      <div className="painel">
        <div className="filtros">
          <div className="campo" style={{ minWidth: 220 }}>
            <label htmlFor="c-busca">Buscar condição</label>
            <input
              id="c-busca"
              value={termo}
              placeholder="ex. diabet, hipert"
              onChange={(e) => setTermo(e.target.value)}
            />
          </div>
          <div className="campo">
            <label htmlFor="c-sexo">Sexo</label>
            <select
              id="c-sexo"
              value={sexo}
              onChange={(e) => {
                setSexo(e.target.value);
                setResultado(null);
              }}
            >
              <option value="">todos</option>
              <option value="M">M</option>
              <option value="F">F</option>
            </select>
          </div>
          <div className="campo">
            <label htmlFor="c-min">Idade mín.</label>
            <input
              id="c-min"
              type="number"
              min={0}
              max={130}
              value={idadeMin}
              onChange={(e) => {
                setIdadeMin(e.target.value);
                setResultado(null);
              }}
            />
          </div>
          <div className="campo">
            <label htmlFor="c-max">Idade máx.</label>
            <input
              id="c-max"
              type="number"
              min={0}
              max={130}
              value={idadeMax}
              onChange={(e) => {
                setIdadeMax(e.target.value);
                setResultado(null);
              }}
            />
          </div>
        </div>

        {sugestoes.data && sugestoes.data.length > 0 && (
          <div className="chips" style={{ marginTop: 12 }}>
            {sugestoes.data.map((s) => (
              <button
                key={s.nome}
                className={`chip ${condicoes.includes(s.nome) ? "ativo" : ""}`}
                onClick={() => alternarCondicao(s.nome)}
              >
                {s.nome} <small>({s.ocorrencias})</small>
              </button>
            ))}
          </div>
        )}

        {condicoes.length > 0 && (
          <div style={{ marginTop: 14 }}>
            <div className="chips">
              {condicoes.map((c) => (
                <button key={c} className="chip ativo" onClick={() => alternarCondicao(c)}>
                  {c} ×
                </button>
              ))}
            </div>
            {condicoes.length > 1 && (
              <label style={{ display: "block", marginTop: 10, fontSize: 13 }}>
                <input
                  type="checkbox"
                  checked={todas}
                  onChange={(e) => {
                    setTodas(e.target.checked);
                    setResultado(null);
                  }}
                  style={{ width: "auto", marginRight: 6 }}
                />
                exigir <strong>todas</strong> as condições (em vez de qualquer uma)
              </label>
            )}
          </div>
        )}
      </div>

      <div className="painel" style={{ display: "flex", gap: 16, alignItems: "center" }}>
        <div>
          <div className="valor" style={{ fontSize: 26, fontWeight: 600 }}>
            {previa.isLoading ? "…" : (previa.data?.total ?? 0)}
          </div>
          <div className="rotulo" style={{ fontSize: 12, color: "var(--texto-suave)" }}>
            pacientes na coorte
          </div>
        </div>
        <button
          className="primario"
          onClick={() => montar.mutate()}
          disabled={montar.isPending}
        >
          {montar.isPending ? "montando…" : "listar pacientes"}
        </button>
      </div>

      {previa.data && (
        <div className="aviso">
          <strong>Filtros aplicados:</strong>
          <ul style={{ margin: "5px 0 0", paddingLeft: 18 }}>
            {previa.data.filtros_aplicados.map((f) => (
              <li key={f}>{f}</li>
            ))}
          </ul>
        </div>
      )}

      {montar.error && <Erro mensagem={(montar.error as Error).message} />}

      {resultado && (
        <>
          <h3>{resultado.total} pacientes</h3>
          {resultado.total === 0 ? (
            <Vazio texto="Nenhum paciente atende a esta combinação." />
          ) : (
            <div className="painel rolagem">
              <table>
                <thead>
                  <tr>
                    <th>Paciente</th>
                    <th>Sexo</th>
                    <th>Idade</th>
                    <th>Raça</th>
                  </tr>
                </thead>
                <tbody>
                  {resultado.itens.map((p) => (
                    <tr key={p.id_pessoa}>
                      <td>
                        <Link to={`/pacientes/${p.id_pessoa}`}>Paciente #{p.id_pessoa}</Link>
                      </td>
                      <td>{p.sexo ?? "—"}</td>
                      <td>{p.idade ?? "—"}</td>
                      <td>{p.raca ?? "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
      {montar.isPending && <Carregando texto="Montando coorte…" />}
    </>
  );
}
