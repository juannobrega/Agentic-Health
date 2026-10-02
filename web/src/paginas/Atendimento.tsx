import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";

import { obter } from "../api/cliente";
import type { AtendimentoDetalhe } from "../api/tipos-dominio";
import { Carregando, Erro, Indisponivel, dataBr } from "../componentes/basicos";

export function Atendimento() {
  const { id } = useParams<{ id: string }>();

  const { data, isLoading, error } = useQuery({
    queryKey: ["atendimento", id],
    queryFn: () => obter<AtendimentoDetalhe>(`/atendimentos/${id}`),
  });

  if (isLoading) return <Carregando />;
  if (error) return <Erro mensagem={(error as Error).message} />;
  if (!data) return null;

  return (
    <>
      <h2>
        Atendimento #{data.id_atendimento} · {data.tipo}
      </h2>
      <p className="subtitulo">
        {dataBr(data.data_inicio)}
        {data.duracao_dias !== null && data.duracao_dias > 0 && ` · ${data.duracao_dias} dias`}
        {" · "}
        <Link to={`/pacientes/${data.id_pessoa}`}>
          Paciente #{data.id_pessoa}
          {data.sexo && data.idade !== null && ` (${data.sexo}, ${data.idade} anos)`}
        </Link>
        {data.id_atendimento_anterior && (
          <>
            {" · "}
            <Link to={`/atendimentos/${data.id_atendimento_anterior}`}>
              atendimento anterior
            </Link>
          </>
        )}
      </p>

      <Secao titulo="Condições" vazio="Nenhuma condição diagnosticada">
        {data.condicoes.map((c) => (
          <li key={c.id_condicao}>
            {c.nome_condicao} <small>({dataBr(c.data_inicio)})</small>
          </li>
        ))}
      </Secao>

      <Secao titulo="Medicamentos" vazio="Nenhum medicamento prescrito">
        {data.medicamentos.map((m) => (
          <li key={m.pk}>
            {m.nome_medicamento}
            {m.dias_fornecimento ? <small> · {m.dias_fornecimento} dias</small> : null}
          </li>
        ))}
      </Secao>

      <Secao titulo="Procedimentos" vazio="Nenhum procedimento realizado">
        {data.procedimentos.map((p) => (
          <li key={p.id_procedimento}>{p.nome_procedimento}</li>
        ))}
      </Secao>

      <Secao
        titulo={`Exames (${data.exames.length})`}
        vazio="Nenhum exame pedido"
        aviso="O dataset não traz resultados: apenas qual exame foi pedido."
        colapsar={data.exames.length > 20}
      >
        {data.exames.map((e) => (
          <li key={e.pk}>
            {e.nome_exame} — <Indisponivel />
          </li>
        ))}
      </Secao>
    </>
  );
}

function Secao({
  titulo,
  vazio,
  aviso,
  colapsar = false,
  children,
}: {
  titulo: string;
  vazio: string;
  aviso?: string;
  colapsar?: boolean;
  children: React.ReactNode;
}) {
  const itens = Array.isArray(children) ? children : [children];
  const temConteudo = itens.flat().filter(Boolean).length > 0;

  const lista = (
    <ul style={{ margin: 0, paddingLeft: 18, fontSize: 13.5, lineHeight: 1.7 }}>
      {children}
    </ul>
  );

  return (
    <>
      <h3>{titulo}</h3>
      <div className="painel">
        {aviso && temConteudo && <div className="aviso">{aviso}</div>}
        {!temConteudo ? (
          <span style={{ color: "var(--texto-suave)", fontSize: 13 }}>{vazio}</span>
        ) : colapsar ? (
          // um atendimento chega a 97 exames: colapsa por padrão
          <details>
            <summary style={{ cursor: "pointer", fontSize: 13.5 }}>
              expandir lista completa
            </summary>
            <div style={{ marginTop: 10 }}>{lista}</div>
          </details>
        ) : (
          lista
        )}
      </div>
    </>
  );
}
