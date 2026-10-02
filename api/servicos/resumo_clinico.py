"""Resumo clínico em texto, por template determinístico (HU-1.6).

NÃO usa LLM: o texto precisa ser factual e reproduzível. A mesma entrada produz
exatamente a mesma saída.

O resumo declara o que NÃO se sabe, não apenas o que se sabe. Omitir que os
exames não têm resultados levaria quem lê a concluir ausência de alteração
(ADR-008).
"""
from datetime import date

SEM_RESULTADO = (
    "Os {n} exames registrados indicam apenas qual exame foi pedido e quando: "
    "este dataset não traz resultados, portanto não há valores laboratoriais "
    "ou de sinais vitais para avaliar. A ausência de valores não significa "
    "ausência de alteração."
)


def _data_br(valor: date | None) -> str:
    return valor.strftime("%d/%m/%Y") if valor else "data não registrada"


def montar(dados: dict) -> str:
    """Monta o resumo a partir do dicionário de `dados_para_resumo`."""
    pessoa = dados["pessoa"]
    idade = dados["idade"]
    contadores = dados["contadores"]
    linhas: list[str] = []

    # --- identificação (pacientes não têm nome — ADR-009)
    linhas.append(f"RESUMO CLÍNICO — PACIENTE #{pessoa.id_pessoa}")
    linhas.append("=" * 64)
    linhas.append("")

    sexo = pessoa.sexo_descricao or pessoa.sexo or "sexo não registrado"
    if idade is not None:
        identificacao = f"{sexo}, {idade} anos"
    else:
        identificacao = (
            f"{sexo}, idade indeterminada "
            f"(ano de nascimento implausível: {pessoa.ano_nascimento})"
        )
    linhas.append(f"Identificação: {identificacao}")
    if pessoa.raca or pessoa.etnia:
        linhas.append(f"Raça/etnia: {pessoa.raca or '—'} / {pessoa.etnia or '—'}")
    linhas.append(f"Código de origem: {pessoa.codigo_origem_pessoa or '—'}")

    janela = dados.get("janela")
    if janela:
        linhas.append(
            f"Janela de observação: {_data_br(janela.data_inicio_periodo)} "
            f"a {_data_br(janela.data_fim_periodo)}"
        )
    linhas.append("")

    # --- alergias primeiro: é o que muda conduta
    linhas.append("ALERGIAS")
    alergias = dados.get("alergias") or []
    if alergias:
        for a in alergias:
            linhas.append(f"  • {a.nome_observacao} (registro em {_data_br(a.data)})")
    else:
        linhas.append("  Nenhuma alergia registrada.")
    linhas.append("")

    # --- condições
    linhas.append(f"CONDIÇÕES ({contadores['condicoes']} registros)")
    condicoes = dados.get("condicoes") or []
    if condicoes:
        for nome, primeira, ocorrencias in condicoes:
            sufixo = f" — {ocorrencias} ocorrências" if ocorrencias > 1 else ""
            linhas.append(f"  • {nome} (desde {_data_br(primeira)}){sufixo}")
    else:
        linhas.append("  Nenhuma condição registrada.")
    linhas.append("")

    # --- medicamentos (só os válidos — ADR-008)
    linhas.append(f"MEDICAMENTOS ({contadores['medicamentos']} registros válidos)")
    medicamentos = dados.get("medicamentos") or []
    if medicamentos:
        for nome, ultima in medicamentos:
            linhas.append(f"  • {nome} (último registro em {_data_br(ultima)})")
    else:
        linhas.append("  Nenhum medicamento registrado.")
    linhas.append("")

    # --- atendimentos recentes
    linhas.append(f"ATENDIMENTOS ({contadores['atendimentos']} no total)")
    atendimentos = dados.get("atendimentos") or []
    if atendimentos:
        linhas.append("  Mais recentes:")
        for data_inicio, descricao in atendimentos:
            linhas.append(f"  • {_data_br(data_inicio)} — {descricao or 'tipo não registrado'}")
    else:
        linhas.append("  Nenhum atendimento registrado.")
    linhas.append("")

    # --- procedimentos
    linhas.append(f"PROCEDIMENTOS: {contadores['procedimentos']} registros")
    linhas.append("")

    # --- a limitação, dita explicitamente (ADR-008)
    linhas.append("EXAMES")
    linhas.append("  " + SEM_RESULTADO.format(n=contadores["exames"]))
    linhas.append("")

    linhas.append("-" * 64)
    linhas.append(
        "Dados sintéticos (Synthea / OMOP CDM). Resumo gerado por template "
        "determinístico a partir do prontuário, sem inferência."
    )

    return "\n".join(linhas)
