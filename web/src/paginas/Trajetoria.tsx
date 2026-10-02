import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";

import { obter } from "../api/cliente";
import type { Trajetoria as TipoTrajetoria } from "../api/tipos-dominio";
import { Carregando, Erro, Vazio, dataBr } from "../componentes/basicos";

export function Trajetoria() {
  const { id } = useParams<{ id: string }>();
  const idPessoa = Number(id);

  const { data, isLoading, error } = useQuery({
    queryKey: ["trajetoria", idPessoa],
    queryFn: () => obter<TipoTrajetoria>(`/pacientes/${idPessoa}/trajetoria`),
  });

  if (isLoading) return <Carregando />;
  if (error) return <Erro mensagem={(error as Error).message} />;
  if (!data) return null;

  return (
    <>
      <h2>Trajetória · Paciente #{idPessoa}</h2>
      <p className="subtitulo">
        {data.total_atendimentos} atendimentos encadeados ·{" "}
        <Link to={`/pacientes/${idPessoa}`}>voltar ao prontuário</Link>
      </p>

      {data.ciclo_detectado && (
        <div className="alerta">
          <strong>Ciclo detectado</strong>
          A cadeia de atendimentos revisita um nó; a sequência foi interrompida.
        </div>
      )}
      {data.truncada && (
        <div className="aviso">
          Sequência truncada no limite de passos — há mais atendimentos encadeados.
        </div>
      )}

      {data.passos.length === 0 ? (
        <Vazio texto="Nenhum atendimento registrado." />
      ) : (
        <div className="painel trilha">
          {data.passos.map((passo) => (
            <div className="passo" key={passo.id_atendimento}>
              {passo.dias_desde_anterior !== null && (
                <div className="intervalo">↓ {passo.dias_desde_anterior} dias</div>
              )}
              {passo.dias_desde_anterior === null && passo.ordem > 1 && (
                <div className="intervalo">↓</div>
              )}
              {passo.ordem === 1 && <div className="intervalo">início</div>}
              <div className="caixa">
                <div className="tipo">{passo.tipo ?? "—"}</div>
                <Link to={`/atendimentos/${passo.id_atendimento}`}>
                  {dataBr(passo.data_inicio)}
                </Link>
                {passo.condicoes.length > 0 && (
                  <div style={{ marginTop: 5, color: "var(--texto-suave)", fontSize: 11.5 }}>
                    {passo.condicoes.slice(0, 2).join(" · ")}
                    {passo.condicoes.length > 2 && ` +${passo.condicoes.length - 2}`}
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </>
  );
}
