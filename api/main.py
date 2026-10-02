"""Aplicação FastAPI do Agentic Health (ADR-004)."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.config import obter_configuracao
from api.db import encerrar_engine, obter_engine
from api.routers import saude

cfg = obter_configuracao()


@asynccontextmanager
async def ciclo_de_vida(app: FastAPI):
    obter_engine()  # cria o pool no startup, não no primeiro request
    yield
    await encerrar_engine()


app = FastAPI(
    title="Agentic Health API",
    description=(
        "API de exploração clínica sobre dados sintéticos no padrão OMOP CDM.\n\n"
        "**Limitações do dataset** (ADR-008): os exames não têm resultados "
        "(`valor_numerico` é sempre nulo); 7.899 registros de medicamento trazem "
        "código de condição e são excluídos por padrão; os pacientes não têm nome, "
        "sendo identificados por `id_pessoa` e UUID.\n\n"
        "**Sem autenticação** (ADR-005): os dados são sintéticos. Não exponha "
        "esta API à internet."
    ),
    version="0.1.0",
    lifespan=ciclo_de_vida,
)

# Sem autenticação, restringir a origem é o que evita que qualquer página
# consuma a API pelo navegador do usuário (ADR-005).
app.add_middleware(
    CORSMiddleware,
    allow_origins=cfg.lista_cors_origens,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(saude.roteador)


@app.get("/", include_in_schema=False)
async def raiz():
    return {"api": "Agentic Health", "documentacao": "/docs", "saude": "/saude"}
