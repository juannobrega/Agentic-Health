# AGENTIC HEALTH

Plataforma de exploração clínica sobre dados sintéticos no padrão OMOP CDM.

**Estado atual:** banco populado e validado. Backend e frontend especificados em
[docs/](docs/), ainda não implementados.

---

## Começando

```bash
cp .env.example .env
pip install -r Data/DB/requirements.txt

docker compose up -d                        # sobe o Postgres
python3 Data/DB/scripts/popular_banco.py    # carrega 312.276 linhas em ~20s
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
├── docker-compose.yml        Postgres (API e frontend a adicionar)
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

## Próximos passos

1. **E5** — plataforma: API e frontend no compose, modelos ORM, migrations,
   tipos gerados e testes de schema
2. **E1** — prontuário e timeline (a base do produto)
3. **E2, E4, E3** — atendimentos, dicionário, coortes

A camada de agente de IA será especificada quando o tema for abordado.

## Segurança

**Sem autenticação** ([ADR-005](docs/adr/ADR-005%20SEM%20AUTENTICACAO.md)) — os
dados são sintéticos e não há o que proteger. Consequência: **a API não pode ser
exposta à internet.** Mantenha em localhost ou rede privada.
