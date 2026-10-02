import { useQuery } from "@tanstack/react-query";

import { obter } from "../api/cliente";
import type { ResumoPopulacional } from "../api/tipos-dominio";
import { Barra, Cartao, Carregando, Erro } from "../componentes/basicos";

export function Dashboard() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["resumo"],
    queryFn: () => obter<ResumoPopulacional>("/estatisticas/resumo"),
  });

  if (isLoading) return <Carregando />;
  if (error) return <Erro mensagem={(error as Error).message} />;
  if (!data) return null;

  const maiorFaixa = Math.max(...data.piramide_etaria.map((f) => f.pacientes), 1);
  const totalAtendimentos = data.atendimentos_por_tipo.reduce((s, t) => s + t.pacientes, 0);

  return (
    <>
      <h2>Visão populacional</h2>
      <p className="subtitulo">Cobertura: {data.janela_temporal}</p>

      {/* o viés da amostra precisa estar visível, não enterrado na doc */}
      <div className="aviso">{data.aviso_representatividade}</div>

      <div className="cartoes">
        <Cartao valor={data.total_pacientes.toLocaleString("pt-BR")} rotulo="pacientes" />
        <Cartao valor={totalAtendimentos.toLocaleString("pt-BR")} rotulo="atendimentos" />
        <Cartao valor={data.pacientes_multimorbidade} rotulo="com 2+ crônicas" />
        {data.atendimentos_por_tipo.map((t) => (
          <Cartao key={t.rotulo} valor={t.pacientes.toLocaleString("pt-BR")} rotulo={t.rotulo.toLowerCase()} />
        ))}
      </div>

      <h3>Distribuição etária</h3>
      <div className="painel">
        {data.piramide_etaria.map((faixa) => (
          <div className="barra-linha" key={faixa.faixa}>
            <span>{faixa.faixa} anos</span>
            <Barra percentual={(100 * faixa.pacientes) / maiorFaixa} />
            <span className="barra-valor">{faixa.pacientes}</span>
          </div>
        ))}
      </div>

      <h3>Sexo e raça</h3>
      <div className="painel">
        {[...data.por_sexo, ...data.por_raca].map((item) => (
          <div className="barra-linha" key={item.rotulo}>
            <span>{item.rotulo}</span>
            <Barra percentual={(100 * item.pacientes) / data.total_pacientes} />
            <span className="barra-valor">{item.pacientes}</span>
          </div>
        ))}
      </div>

      {/* nenhum gráfico de valor de exame: o dado não existe (ADR-008) */}
      <div className="aviso">
        Este dataset não traz resultados de exame, portanto não há indicadores
        laboratoriais, de pressão arterial ou de IMC.
      </div>
    </>
  );
}
