import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useParams } from "react-router-dom";

import { obter, obterTexto } from "../api/cliente";
import type {
  EventoTimeline,
  ItemAlergia,
  ItemCondicao,
  ItemExame,
  ItemProcedimento,
  ListaMedicamentos,
  Pagina,
  PacienteDetalhe,
  TipoEvento,
} from "../api/tipos-dominio";
import {
  AvisoQualidade,
  Carregando,
  Erro,
  Indisponivel,
  Paginacao,
  Vazio,
  dataBr,
} from "../componentes/basicos";
import { Timeline } from "../componentes/Timeline";

type Aba = "timeline" | "condicoes" | "medicamentos" | "procedimentos" | "exames" | "resumo";

const TIPOS: TipoEvento[] = ["condicao", "medicamento", "procedimento", "exame"];

export function Prontuario() {
  const { id } = useParams<{ id: string }>();
  const idPessoa = Number(id);
  const [aba, setAba] = useState<Aba>("timeline");

  const paciente = useQuery({
    queryKey: ["paciente", idPessoa],
    queryFn: () => obter<PacienteDetalhe>(`/pacientes/${idPessoa}`),
  });

  const alergias = useQuery({
    queryKey: ["alergias", idPessoa],
    queryFn: () => obter<ItemAlergia[]>(`/pacientes/${idPessoa}/alergias`),
  });

  if (paciente.isLoading) return <Carregando />;
  if (paciente.error) return <Erro mensagem={(paciente.error as Error).message} />;
  if (!paciente.data) return null;

  const p = paciente.data;
  const c = p.contadores;

  return (
    <>
      <h2>Paciente #{p.id_pessoa}</h2>
      <p className="subtitulo">
        {p.sexo_descricao ?? p.sexo ?? "—"}
        {p.idade !== null ? `, ${p.idade} anos` : ", idade indeterminada"} ·{" "}
        {p.raca ?? "—"} / {p.etnia ?? "—"} ·{" "}
        <span style={{ fontSize: 11.5 }}>{p.codigo_origem_pessoa}</span>
      </p>

      {/* ano de nascimento implausível: o dado existe, com aviso (HU-1.2) */}
      {p.aviso && <div className="aviso">{p.aviso}</div>}

      {/* alergias no cabeçalho, não só numa aba: é o que muda conduta */}
      {alergias.data && alergias.data.length > 0 && (
        <div className="alerta">
          <strong>Alergias</strong>
          {alergias.data.map((a) => a.nome_observacao).join(" · ")}
        </div>
      )}

      <div className="cartoes">
        <div className="cartao">
          <div className="valor">{c.atendimentos}</div>
          <div className="rotulo">atendimentos</div>
        </div>
        <div className="cartao">
          <div className="valor">{c.condicoes}</div>
          <div className="rotulo">condições</div>
        </div>
        <div className="cartao">
          <div className="valor">{c.medicamentos}</div>
          <div className="rotulo">medicamentos</div>
        </div>
        <div className="cartao">
          <div className="valor">{c.procedimentos}</div>
          <div className="rotulo">procedimentos</div>
        </div>
        <div className="cartao">
          <div className="valor">{c.exames.toLocaleString("pt-BR")}</div>
          <div className="rotulo">exames pedidos</div>
        </div>
      </div>

      {p.janela_observacao && (
        <p className="subtitulo" style={{ marginTop: 14 }}>
          Janela de observação: {dataBr(p.janela_observacao.data_inicio)} a{" "}
          {dataBr(p.janela_observacao.data_fim)} ·{" "}
          <Link to={`/pacientes/${idPessoa}/trajetoria`}>ver trajetória</Link>
        </p>
      )}

      <nav className="abas">
        {(
          [
            ["timeline", "Timeline"],
            ["condicoes", `Condições (${c.condicoes})`],
            ["medicamentos", `Medicamentos (${c.medicamentos})`],
            ["procedimentos", `Procedimentos (${c.procedimentos})`],
            ["exames", `Exames (${c.exames})`],
            ["resumo", "Resumo"],
          ] as [Aba, string][]
        ).map(([chave, rotulo]) => (
          <button
            key={chave}
            className={aba === chave ? "ativo" : ""}
            onClick={() => setAba(chave)}
          >
            {rotulo}
          </button>
        ))}
      </nav>

      {aba === "timeline" && <AbaTimeline idPessoa={idPessoa} />}
      {aba === "condicoes" && <AbaCondicoes idPessoa={idPessoa} />}
      {aba === "medicamentos" && <AbaMedicamentos idPessoa={idPessoa} />}
      {aba === "procedimentos" && <AbaProcedimentos idPessoa={idPessoa} />}
      {aba === "exames" && <AbaExames idPessoa={idPessoa} />}
      {aba === "resumo" && <AbaResumo idPessoa={idPessoa} />}
    </>
  );
}

function AbaTimeline({ idPessoa }: { idPessoa: number }) {
  const [pagina, setPagina] = useState(1);
  const [tipos, setTipos] = useState<TipoEvento[]>([]);

  const { data, isLoading, error } = useQuery({
    queryKey: ["timeline", idPessoa, pagina, tipos],
    queryFn: () =>
      obter<Pagina<EventoTimeline>>(`/pacientes/${idPessoa}/timeline`, {
        pagina,
        por_pagina: 50,
        tipo: tipos.length ? tipos : undefined,
      }),
  });

  function alternar(tipo: TipoEvento) {
    setPagina(1);
    setTipos((atual) =>
      atual.includes(tipo) ? atual.filter((t) => t !== tipo) : [...atual, tipo],
    );
  }

  return (
    <>
      <div className="chips" style={{ marginBottom: 14 }}>
        {TIPOS.map((tipo) => (
          <button
            key={tipo}
            className={`chip ${tipos.includes(tipo) ? "ativo" : ""}`}
            onClick={() => alternar(tipo)}
          >
            {tipo}
          </button>
        ))}
      </div>

      {isLoading && <Carregando />}
      {error && <Erro mensagem={(error as Error).message} />}
      {data && data.total === 0 && <Vazio texto="Nenhum evento no período." />}
      {data && data.total > 0 && (
        <>
          <div className="painel">
            <Timeline eventos={data.itens} />
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

function AbaCondicoes({ idPessoa }: { idPessoa: number }) {
  const [pagina, setPagina] = useState(1);
  const { data, isLoading } = useQuery({
    queryKey: ["condicoes", idPessoa, pagina],
    queryFn: () =>
      obter<Pagina<ItemCondicao>>(`/pacientes/${idPessoa}/condicoes`, { pagina }),
  });
  if (isLoading) return <Carregando />;
  if (!data) return null;
  if (data.total === 0) return <Vazio texto="Nenhuma condição registrada." />;
  return (
    <>
      <div className="painel rolagem">
        <table>
          <thead>
            <tr>
              <th>Condição</th>
              <th>Início</th>
              <th>Fim</th>
              <th>Atendimento</th>
            </tr>
          </thead>
          <tbody>
            {data.itens.map((i) => (
              <tr key={i.id_condicao}>
                <td>{i.nome_condicao ?? "—"}</td>
                <td>{dataBr(i.data_inicio)}</td>
                <td>{dataBr(i.data_fim)}</td>
                <td>
                  {i.id_atendimento ? (
                    <Link to={`/atendimentos/${i.id_atendimento}`}>#{i.id_atendimento}</Link>
                  ) : (
                    "—"
                  )}
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
  );
}

function AbaMedicamentos({ idPessoa }: { idPessoa: number }) {
  const [pagina, setPagina] = useState(1);
  const { data, isLoading } = useQuery({
    queryKey: ["medicamentos", idPessoa, pagina],
    queryFn: () =>
      obter<ListaMedicamentos>(`/pacientes/${idPessoa}/medicamentos`, { pagina }),
  });
  if (isLoading) return <Carregando />;
  if (!data) return null;
  return (
    <>
      {/* o filtro de qualidade é informado, não silencioso (ADR-008) */}
      <AvisoQualidade filtro={data.filtro_qualidade} />
      {data.total === 0 ? (
        <Vazio texto="Nenhum medicamento registrado." />
      ) : (
        <>
          <div className="painel rolagem">
            <table>
              <thead>
                <tr>
                  <th>Medicamento</th>
                  <th>Início</th>
                  <th>Fim</th>
                  <th>Dias</th>
                </tr>
              </thead>
              <tbody>
                {data.itens.map((i) => (
                  <tr key={i.pk}>
                    <td>{i.nome_medicamento ?? "—"}</td>
                    <td>{dataBr(i.data_inicio)}</td>
                    <td>{dataBr(i.data_fim)}</td>
                    <td>{i.dias_fornecimento ?? "—"}</td>
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

function AbaProcedimentos({ idPessoa }: { idPessoa: number }) {
  const [pagina, setPagina] = useState(1);
  const { data, isLoading } = useQuery({
    queryKey: ["procedimentos", idPessoa, pagina],
    queryFn: () =>
      obter<Pagina<ItemProcedimento>>(`/pacientes/${idPessoa}/procedimentos`, { pagina }),
  });
  if (isLoading) return <Carregando />;
  if (!data) return null;
  if (data.total === 0) return <Vazio texto="Nenhum procedimento registrado." />;
  return (
    <>
      <div className="painel rolagem">
        <table>
          <thead>
            <tr>
              <th>Procedimento</th>
              <th>Data</th>
              <th>Atendimento</th>
            </tr>
          </thead>
          <tbody>
            {data.itens.map((i) => (
              <tr key={i.id_procedimento}>
                <td>{i.nome_procedimento ?? "—"}</td>
                <td>{dataBr(i.data)}</td>
                <td>
                  {i.id_atendimento ? (
                    <Link to={`/atendimentos/${i.id_atendimento}`}>#{i.id_atendimento}</Link>
                  ) : (
                    "—"
                  )}
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
  );
}

function AbaExames({ idPessoa }: { idPessoa: number }) {
  const [pagina, setPagina] = useState(1);
  const { data, isLoading } = useQuery({
    queryKey: ["exames", idPessoa, pagina],
    queryFn: () => obter<Pagina<ItemExame>>(`/pacientes/${idPessoa}/exames`, { pagina }),
  });
  if (isLoading) return <Carregando />;
  if (!data) return null;
  return (
    <>
      {/* a limitação mais severa do dataset, dita na própria tela (ADR-008) */}
      <div className="aviso">
        Este dataset registra qual exame foi pedido e quando, mas{" "}
        <strong>não traz os resultados</strong>. A ausência de valores não
        significa ausência de alteração.
      </div>
      {data.total === 0 ? (
        <Vazio texto="Nenhum exame registrado." />
      ) : (
        <>
          <div className="painel rolagem">
            <table>
              <thead>
                <tr>
                  <th>Exame</th>
                  <th>Data</th>
                  <th>Resultado</th>
                  <th>Atendimento</th>
                </tr>
              </thead>
              <tbody>
                {data.itens.map((i) => (
                  <tr key={i.pk}>
                    <td>{i.nome_exame ?? "—"}</td>
                    <td>{dataBr(i.data)}</td>
                    <td>
                      <Indisponivel />
                    </td>
                    <td>
                      {i.id_atendimento ? (
                        <Link to={`/atendimentos/${i.id_atendimento}`}>
                          #{i.id_atendimento}
                        </Link>
                      ) : (
                        "—"
                      )}
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

function AbaResumo({ idPessoa }: { idPessoa: number }) {
  const { data, isLoading } = useQuery({
    queryKey: ["resumo-clinico", idPessoa],
    queryFn: () => obterTexto(`/pacientes/${idPessoa}/resumo`),
  });
  const [copiado, setCopiado] = useState(false);

  if (isLoading) return <Carregando />;
  if (!data) return null;

  return (
    <>
      <button
        style={{ marginBottom: 12 }}
        onClick={() => {
          void navigator.clipboard?.writeText(data).then(
            () => {
              setCopiado(true);
              setTimeout(() => setCopiado(false), 2000);
            },
            () => setCopiado(false),
          );
        }}
      >
        {copiado ? "copiado" : "copiar texto"}
      </button>
      <pre className="resumo">{data}</pre>
    </>
  );
}
