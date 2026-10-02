/**
 * Cliente HTTP da API.
 *
 * Em desenvolvimento o Vite faz proxy de /api para o backend, então a origem é
 * única e não há CORS. Em produção VITE_API_URL aponta para a API.
 */
const BASE = import.meta.env.VITE_API_URL ?? "/api";

export class ErroApi extends Error {
  constructor(
    readonly status: number,
    readonly detalhe: string,
  ) {
    super(detalhe);
  }
}

type Parametros = Record<string, string | number | boolean | undefined | null | string[]>;

function montarBusca(parametros?: Parametros): string {
  if (!parametros) return "";
  const busca = new URLSearchParams();
  for (const [chave, valor] of Object.entries(parametros)) {
    if (valor === undefined || valor === null || valor === "") continue;
    // parâmetros repetidos (ex. tipo=exame&tipo=condicao)
    if (Array.isArray(valor)) {
      for (const item of valor) busca.append(chave, item);
    } else {
      busca.append(chave, String(valor));
    }
  }
  const texto = busca.toString();
  return texto ? `?${texto}` : "";
}

async function tratar<T>(resposta: Response): Promise<T> {
  if (!resposta.ok) {
    let detalhe = `Falha na requisição (${resposta.status})`;
    try {
      const corpo = await resposta.json();
      if (typeof corpo?.detail === "string") detalhe = corpo.detail;
    } catch {
      // resposta sem JSON — mantém a mensagem padrão
    }
    throw new ErroApi(resposta.status, detalhe);
  }
  return resposta.json() as Promise<T>;
}

export async function obter<T>(caminho: string, parametros?: Parametros): Promise<T> {
  return tratar<T>(await fetch(`${BASE}${caminho}${montarBusca(parametros)}`));
}

export async function obterTexto(caminho: string): Promise<string> {
  const resposta = await fetch(`${BASE}${caminho}`);
  if (!resposta.ok) throw new ErroApi(resposta.status, `Falha (${resposta.status})`);
  return resposta.text();
}

export async function enviar<T>(
  caminho: string,
  corpo: unknown,
  parametros?: Parametros,
): Promise<T> {
  return tratar<T>(
    await fetch(`${BASE}${caminho}${montarBusca(parametros)}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(corpo),
    }),
  );
}
