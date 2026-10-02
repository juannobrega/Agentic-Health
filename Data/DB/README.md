# Banco de dados — Synthea PT no Postgres

Sobe um Postgres em Docker e carrega o dataset [`Data/Synthea`](../Synthea)
(OMOP CDM traduzido para português) — **312.276 linhas em ~20s**.

## Subir

As credenciais vêm do **`.env` único na raiz do projeto**. Use o `Makefile` da raiz:

```bash
cp .env.example .env                      # na raiz
pip install -r Data/DB/requirements.txt
make up        # sobe o Postgres e espera ficar healthy
make popular   # carrega as 312.276 linhas
```

> O `docker compose` direto **não** lê o `.env` da raiz sozinho (precisaria de
> `--env-file ../../.env`). Os alvos do Makefile já passam a flag — prefira-os,
> ou o compose cairá nos valores default e ignorará suas credenciais.

Conexão padrão: `localhost:5432`, banco `agentic_health`, usuário/senha `postgres`
— tudo configurável no `.env` da raiz (inclusive a porta).
Todas as tabelas ficam no schema **`synthea`**.

```bash
make psql       # ou: docker exec -it agentic-health-db psql -U postgres -d agentic_health
```
```sql
SET search_path TO synthea;
SELECT nome_condicao, count(*) FROM condicao GROUP BY 1 ORDER BY 2 DESC LIMIT 10;
```

## Comandos

Rodando da **raiz** do projeto:

| Comando | O que faz |
|---|---|
| `make up` | Sobe o Postgres e aguarda o healthcheck |
| `make popular` | Carrega. Recusa se já houver dados |
| `make verificar` | Valida o conteúdo do banco |
| `make psql` | Abre o psql |
| `make logs` | Acompanha os logs |
| `make down` | Para o container (dados preservados) |
| `make reset` | Apaga o volume e recarrega do zero |

Para recarregar sem apagar o volume:
`python3 Data/DB/scripts/popular_banco.py --recriar`

## Estrutura

```
Data/DB/
├── docker-compose.yml       Postgres 17-alpine + healthcheck + volume
├── requirements.txt         psycopg[binary], python-dotenv
├── sql/                     aplicado automaticamente na 1ª subida
│   ├── 01_schema.sql        11 tabelas
│   ├── 02_indices.sql       índices de consulta
│   └── 03_views.sql         views com os filtros de qualidade
└── scripts/popular_banco.py carga via COPY + validação
```

## Tabelas

`pessoa` · `atendimento` · `periodo_observacao` · `condicao` ·
`exposicao_medicamento` · `procedimento` · `exame` · `observacao` ·
`periodo_condicao` · `periodo_medicamento` · `dicionario_conceitos`

## Views

Aplicam os filtros de qualidade documentados no [README do dataset](../Synthea/README.md),
para não repetir as mesmas ressalvas em toda consulta.

| View | Para que serve |
|---|---|
| `vw_pessoa_valida` | Exclui os 2 anos de nascimento impossíveis; adiciona `idade` |
| `vw_medicamento_valido` | Só os 21.619 medicamentos RxNorm reais (ver ressalva 2) |
| `vw_atendimento_resumo` | Um atendimento por linha com contagens de condições, exames etc. |

## Migrations

O schema existe em **duas fontes** que precisam concordar (ADR-006):

| Fonte | Papel |
|---|---|
| `sql/01_schema.sql` + `02_indices.sql` | Bootstrap do container, roda no initdb |
| `api/migrations/` | Histórico versionado via Alembic |

```bash
cd api
python3 -m alembic check          # os modelos ORM batem com o banco?
python3 -m alembic current        # revisão aplicada
python3 -m alembic upgrade head   # aplica pendentes
```

**Ao mudar o schema**, altere as duas fontes. O teste
`api/tests/test_schema.py` cria um banco por cada caminho e compara colunas e
índices — divergência falha o build. Hoje as duas produzem **162 colunas e 37
índices idênticos**.

As views ficam fora das migrations: vivem em `sql/03_views.sql` e são aplicadas
pelo initdb. O autogenerate do Alembic as ignora.

## ⚠️ Ressalvas do dataset

Limitações do **Synthea original**, não da carga. O `--verificar` checa todas.

**1. `exame` não tem resultados.** As 199.514 linhas têm `valor_numerico` 100% NULL —
os resultados se perderam no ETL original. Serve só como "exame foi pedido".

**2. 7.899 medicamentos têm código de condição.** 26,8% de `exposicao_medicamento`
traz SNOMED de diagnóstico onde deveria haver RxNorm. Marcados em
`inconsistencia_vocabulario`; use `vw_medicamento_valido` para filtrar.

**3. IDs primários duplicados em 3 tabelas.** O Synthea repete ids apontando para
registros clinicamente distintos:

| Tabela | IDs repetidos |
|---|---|
| `exame` | 29.471 |
| `exposicao_medicamento` | 7.899 |
| `observacao` | 619 |

Por isso essas três têm uma **chave substituta `pk`** (identity) como primary key, e
o id original fica como coluna indexada **sem UNIQUE**. Nenhuma linha foi descartada.
Ao fazer join nessas tabelas, use `pk` — o id original não identifica uma linha.

**4. Outros.** 2 anos de nascimento impossíveis (`id_pessoa` 265 e 332) ·
`observacao` com 83% de conceitos não mapeados · `id_local`/`id_profissional`/
`id_unidade_saude` 100% vazios · raça 75% branca.

## Detalhes de implementação

- **COPY, não INSERT** — as 199k linhas de `exame` entram em ~14s.
- **`''` → NULL** e **`0` → NULL** nas FKs opcionais, onde o OMOP usa 0 como
  sentinela de "sem referência" (viraria violação de FK).
- **Ordem de carga** respeita as FKs: `pessoa` e `atendimento` primeiro.
- **Validação pós-carga** confere contagens, integridade referencial e as
  ressalvas acima; sai com código 1 se algo divergir.
