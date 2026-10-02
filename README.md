# AGENTIC HEALTH

Plataforma de exploração clínica sobre dados sintéticos no padrão OMOP CDM.

**Estado atual:** stack completo funcionando — Postgres, API FastAPI com 24
endpoints e frontend React com 8 telas. 109 testes passando.

---

## Começando

```bash
cp .env.example .env
docker compose up -d                        # Postgres + API + frontend
python3 Data/DB/scripts/popular_banco.py    # carrega 312.276 linhas em ~20s
```

| Serviço | URL |
|---|---|
| Frontend | http://localhost:8081 |
| API | http://localhost:8000 · [/docs](http://localhost:8000/docs) |
| Postgres | localhost:5432 |

Para desenvolver com hot-reload:

```bash
pip install -r api/requirements-dev.txt
python3 -m uvicorn api.main:app --reload    # API em :8000
cd web && npm install && npm run dev        # frontend em :5173
```

Conexão: `localhost:5432` · banco `agentic_health` · usuário/senha `postgres`
— configurável no `.env` da raiz, inclusive a porta.

```bash
docker exec -it agentic-health-db psql -U postgres -d agentic_health
```
```sql
SET search_path TO synthea;
SELECT nome_condicao, count(*) FROM condicao GROUP BY 1 ORDER BY 2 DESC LIMIT 10;
```

## Estrutura

```
.
├── .env                      configuração ÚNICA (ADR-003)
├── docker-compose.yml        Postgres + API + frontend
├── api/                      FastAPI + SQLAlchemy
│   ├── modelos/              ORM (forma do banco)
│   ├── esquemas/             Pydantic (forma da API)
│   ├── repositorios/         acesso a dados
│   ├── routers/              rotas por domínio
│   ├── servicos/             resumo clínico
│   ├── migrations/           Alembic
│   └── tests/                109 testes
├── web/                      React + Vite + TypeScript
│   ├── src/api/              cliente e tipos (tipos.ts é gerado)
│   ├── src/paginas/          8 telas
│   └── src/componentes/
├── Data/
│   ├── Synthea/              dataset traduzido — 10 CSVs + dicionário
│   └── DB/                   schema SQL, índices, views e script de carga
└── docs/
    ├── adr/                  9 Architecture Decision Records
    └── hu/                   24 Histórias de Usuário em 5 épicos
```

## Os dados

**1.130 pacientes · 311.741 registros · 1909 a janeiro de 2019**

Dataset [Synthea](https://github.com/synthetichealth/synthea) (sintético) no
padrão OMOP CDM v5.x, traduzido para português: tabelas, colunas, valores
demográficos e os 535 códigos clínicos SNOMED CT, LOINC e RxNorm.

| Domínio | Registros | Distintos |
|---|---|---|
| Exames | 199.514 | 240 |
| Atendimentos | 32.153 | 3 tipos |
| Medicamentos | 29.518 (21.619 válidos) | 145 |
| Procedimentos | 17.333 | 91 |
| Observações | 8.518 (619 alergias) | — |
| Condições | 7.900 | 134 |

## ⚠️ Limitações que definem o escopo

Limitações do **dataset original**, não da carga. Detalhadas em
[ADR-008](docs/adr/ADR-008%20LIMITACOES%20DOS%20DADOS%20EXPLICITAS%20NA%20UI.md).

**1. Exames não têm resultados.** As 199.514 linhas têm `valor_numerico` 100%
nulo — os valores se perderam no ETL do Synthea. Não há como fazer gráfico de
tendência, controle pressórico, IMC ou fenotipagem por limiar.

**2. 7.899 medicamentos têm código de condição** (26,8%). Use sempre
`vw_medicamento_valido`.

**3. IDs primários duplicados** em `exame`, `exposicao_medicamento` e
`observacao`. O identificador real é a coluna `pk` — e é ela que os modelos
SQLAlchemy declaram como primary key.

**4. Sem dimensão geográfica ou de prestador.** Raça 75% branca — inadequado
para análise de equidade.

## Documentação

| Documento | Conteúdo |
|---|---|
| [docs/adr/](docs/adr/) | 9 decisões de arquitetura e seus motivos |
| [docs/hu/](docs/hu/) | 24 histórias de usuário em 5 épicos |
| [Data/Synthea/README.md](Data/Synthea/README.md) | O dataset e suas ressalvas |
| [Data/DB/README.md](Data/DB/README.md) | Schema, views e carga |

## Testes

```bash
pip install -r api/requirements-dev.txt
python3 -m pytest api/tests/ -q      # 109 testes
cd web && npm run build              # tsc + vite
```

Os testes rodam contra o banco real e cobrem as garantias estruturais: chave
substituta como primary key, ausência de N+1, comparação entre as duas fontes de
schema, e as premissas do dataset (exames sem valor, 7.899 medicamentos
excluídos, 1.128 pacientes válidos).

## Próximos passos

Os 5 épicos planejados estão implementados. A camada de agente de IA será
especificada quando o tema for abordado — ver "Temas ainda sem ADR" no
[índice das ADRs](docs/adr/README.md).

## Segurança

**Sem autenticação** ([ADR-005](docs/adr/ADR-005%20SEM%20AUTENTICACAO.md)) — os
dados são sintéticos e não há o que proteger. Consequência: **a API não pode ser
exposta à internet.** Mantenha em localhost ou rede privada.
