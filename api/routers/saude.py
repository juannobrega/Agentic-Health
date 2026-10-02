"""Endpoints de saúde e validação do ambiente (HU-5.1, HU-5.6)."""
from fastapi import APIRouter, Depends
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from api import modelos
from api.db import obter_sessao
from api.esquemas.comum import ContagemTabela, StatusDados, StatusSaude

roteador = APIRouter(tags=["saúde"])

# contagens esperadas do dataset carregado (ADR-002)
CONTAGENS_ESPERADAS: dict[type, int] = {
    modelos.Pessoa: 1130,
    modelos.PeriodoObservacao: 1126,
    modelos.Atendimento: 32153,
    modelos.Condicao: 7900,
    modelos.ExposicaoMedicamento: 29518,
    modelos.Procedimento: 17333,
    modelos.Exame: 199514,
    modelos.Observacao: 8518,
    modelos.PeriodoCondicao: 7897,
    modelos.PeriodoMedicamento: 6652,
    modelos.DicionarioConceito: 535,
}


@roteador.get("/saude", response_model=StatusSaude, summary="Saúde da API")
async def saude(sessao: AsyncSession = Depends(obter_sessao)) -> StatusSaude:
    try:
        await sessao.execute(text("SELECT 1"))
    except Exception as erro:  # noqa: BLE001 — o endpoint reporta, não propaga
        return StatusSaude(
            status="degradado", banco_conectado=False, detalhe=str(erro)[:200]
        )
    return StatusSaude(status="ok", banco_conectado=True)


@roteador.get(
    "/saude/dados",
    response_model=StatusDados,
    summary="Validação do dataset carregado",
    description=(
        "Confere as contagens das 11 tabelas contra o esperado. Um banco "
        "parcialmente carregado é pior que vazio: as telas funcionam, mas os "
        "números estão errados."
    ),
)
async def saude_dados(sessao: AsyncSession = Depends(obter_sessao)) -> StatusDados:
    tabelas: list[ContagemTabela] = []
    for modelo, esperado in CONTAGENS_ESPERADAS.items():
        linhas = await sessao.scalar(select(func.count()).select_from(modelo)) or 0
        tabelas.append(
            ContagemTabela(
                tabela=modelo.__tablename__,
                linhas=linhas,
                esperado=esperado,
                conforme=linhas == esperado,
            )
        )

    total = sum(t.linhas for t in tabelas)
    conforme = all(t.conforme for t in tabelas)

    if total == 0:
        resumo = "Banco vazio. Rode: python3 Data/DB/scripts/popular_banco.py"
    elif conforme:
        resumo = f"Dataset completo: {total} linhas conforme o esperado."
    else:
        divergentes = [t.tabela for t in tabelas if not t.conforme]
        resumo = (
            f"Carga incompleta ou divergente em: {', '.join(divergentes)}. "
            f"Rode: python3 Data/DB/scripts/popular_banco.py --recriar"
        )

    return StatusDados(
        carregado=total > 0, conforme=conforme, resumo=resumo, tabelas=tabelas
    )
