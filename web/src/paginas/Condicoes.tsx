import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router-dom";

import { obter } from "../api/cliente";
import type { ListaPrevalencia } from "../api/tipos-dominio";
import { AvisoQualidade, Barra, Carregando, Erro, Paginacao } from "../componentes/basicos";

type Dominio = "condicoes" | "medicamentos" | "procedimentos" | "exames";

const ROTULOS: Record<Dominio, string> = {
  condicoes: "Condições",
  medicamentos: "Medicamentos",
  procedimentos: "Procedimentos",
  exames: "Exames",
};

export function Condicoes() {
  const [dominio, setDominio] = useState<Dominio>("condicoes");
  const [pagina, setPagina] = useState(1);
  const [sexo, setSexo] = useState("");
  const [idadeMin, setIdadeMin] = useState("");

  const { data, isLoading, error } = useQuery({
    queryKey: ["prevalencia", dominio, pagina, sexo, idadeMin],
    queryFn: () =>
      obter<ListaPrevalencia>(`/estatisticas/${dominio}`, {
        pagina,
        por_pagina: 25,
        sexo: sexo || undefined,
        idade_min: idadeMin || undefined,
      }),
  });

  return (
    <>
      <h2>Prevalência</h2>
      <p className="subtitulo">
        Ocorrências e pacientes distintos são métricas diferentes: uma condição
        pode se repetir no mesmo paciente. O percentual é sobre pacientes.
      </p>

      <nav className="abas">
        {(Object.keys(ROTULOS) as Dominio[]).map((d) => (
          <button
            key={d}
            className={dominio === d ? "ativo" : ""}
            onClick={() => {
              setDominio(d);
              setPagina(1);
            }}
          >
            {ROTULOS[d]}
          </button>
        ))}
      </nav>

      <div className="painel filtros">
        <div className="campo">
          <label htmlFor="p-sexo">Sexo</label>
          <select
            id="p-sexo"
            value={sexo}
            onChange={(e) => {
              setSexo(e.target.value);
              setPagina(1);
            }}
          >
            <option value="">todos</option>
            <option value="M">M</option>
            <option value="F">F</option>
          </select>
        </div>
        <div className="campo">
          <label htmlFor="p-idade">Idade mín.</label>
          <input
            id="p-idade"
            type="number"
            min={0}
            max={130}
            value={idadeMin}
            onChange={(e) => {
              setIdadeMin(e.target.value);
              setPagina(1);
            }}
          />
        </div>
      </div>

      {isLoading && <Carregando />}
      {error && <Erro mensagem={(error as Error).message} />}

      {data && (
        <>
          <AvisoQualidade filtro={data.filtro_qualidade} />
          <p className="subtitulo">
            {data.total} itens distintos · denominador: {data.denominador} pacientes
          </p>
          <div className="painel">
            {data.itens.map((item) => (
              <div className="barra-linha" key={item.nome}>
                <span>
                  {dominio === "condicoes" ? (
                    <Link to={`/pacientes?condicao=${encodeURIComponent(item.nome)}`}>
                      {item.nome}
                    </Link>
                  ) : (
                    item.nome
                  )}
                </span>
                <Barra percentual={item.percentual_pacientes} />
                <span className="barra-valor">
                  {item.pacientes} pac · {item.ocorrencias} ocor
                </span>
              </div>
            ))}
          </div>
          <Paginacao
            pagina={pagina}
            porPagina={25}
            total={data.total}
            onMudar={setPagina}
          />
        </>
      )}
    </>
  );
}
