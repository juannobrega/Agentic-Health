# ADR-002 POSTGRES EM DOCKER COM CARGA VIA COPY

| | |
|---|---|
| **Status** | Aceita |
| **Data** | 2026-10-02 |
| **Impacto** | Backend, performance de consulta, setup de ambiente |
| **Depende de** | ADR-001 |

---

## 1. Contexto

Os 311.741 registros do dataset vivem em CSV. As consultas que o produto precisa
fazer não são compatíveis com leitura de arquivo:

- **Timeline de um paciente** une 5 tabelas filtrando por `id_pessoa`
- **Prevalência de condições** agrupa 7.900 linhas com corte demográfico
- **Coorte** combina filtros sobre condição, medicamento, idade e sexo

Ler e parsear 22MB de `exame.csv` a cada request é inviável. Sem índice, cada
filtro por paciente varre a tabela inteira.

A maior tabela tem **199.514 linhas**. Uma carga ingênua via `INSERT` linha a
linha levaria minutos — inaceitável para um ambiente que precisa ser recriado
com frequência durante o desenvolvimento.

## 2. Decisão

**Postgres 17-alpine** em Docker Compose, schema dedicado `synthea`, carga via
`COPY ... FROM STDIN` em psycopg 3.

### 2.1 Estrutura

```
docker-compose.yml          ← na RAIZ (ver ADR-003)
Data/DB/
├── sql/
│   ├── 01_schema.sql       11 tabelas
│   ├── 02_indices.sql      índices de consulta
│   └── 03_views.sql        3 views de qualidade
└── scripts/popular_banco.py
```

Os arquivos em `sql/` são montados em `/docker-entrypoint-initdb.d` e executados
**automaticamente** na primeira subida do container — o schema existe antes de
qualquer carga.

### 2.2 Carga via COPY

Medido no ambiente real: **312.276 linhas em 19,6s**, sendo 13,66s só da tabela
`exame`. A mesma carga por `INSERT` individual seria ~100x mais lenta.

O script converte dois casos que quebrariam a carga:

- **`''` → `NULL`** — CSV não distingue vazio de nulo; colunas `DATE` e `NUMERIC`
  rejeitam string vazia
- **`0` → `NULL`** nas FKs opcionais (`id_atendimento`, `id_profissional`,
  `id_unidade_saude`, `id_local`, `id_detalhe_atendimento`,
  `id_atendimento_anterior`) — o OMOP usa `0` como sentinela de "sem
  referência", mas `0` não existe como chave e violaria a FK

### 2.3 Chave substituta em três tabelas

**Esta é a parte não óbvia da decisão.** O dataset original repete IDs que
deveriam ser únicos:

| Tabela | Linhas | IDs distintos | Repetidos |
|---|---|---|---|
| `exame` | 199.514 | 170.043 | **29.471** |
| `exposicao_medicamento` | 29.518 | 13.799 | **7.899** |
| `observacao` | 8.518 | 7.899 | **619** |

As linhas que compartilham ID **não são duplicatas** — são registros clínicos
distintos. Exemplo real, `id_exposicao_medicamento = 1`:

```
pessoa=1  2013-07-05  43878008  Faringite estreptocócica
pessoa=1  2013-07-05  834102    Naproxeno 500mg
pessoa=1  2011-08-19  140       Acetaminofeno (paracetamol)
```

Nenhum par de linhas duplicadas é idêntico. Descartá-las perderia dado clínico real.

Solução: essas três tabelas ganham `pk BIGINT GENERATED ALWAYS AS IDENTITY
PRIMARY KEY`, e o ID original fica como coluna **indexada sem UNIQUE**.

### 2.4 Views de qualidade

Três views encapsulam filtros que, de outro modo, teriam de ser repetidos em
toda consulta (ver ADR-008):

| View | O que faz |
|---|---|
| `vw_pessoa_valida` | Exclui os 2 anos de nascimento impossíveis; calcula `idade` |
| `vw_medicamento_valido` | Só os 21.619 medicamentos RxNorm reais |
| `vw_atendimento_resumo` | Um atendimento por linha com contadores por domínio |

### 2.5 Validação pós-carga

O script roda automaticamente ao final e sai com **código 1** se algo divergir:

- Contagem exata de cada uma das 11 tabelas
- Integridade referencial (órfãos de `id_pessoa` e `id_atendimento`)
- As ressalvas conhecidas: exames com valor (esperado 0), medicamentos
  inconsistentes (esperado 7.899), pacientes válidos (1.128 de 1.130)

## 3. Alternativas descartadas

| Alternativa | Por que não |
|---|---|
| **SQLite** | Sem tipos rígidos nem `COPY`; concorrência de escrita limitada. Ganho de simplicidade não compensa num projeto que já usa Docker |
| **DuckDB** | Excelente para analítica sobre CSV, e tentador aqui. Descartado porque o backend precisa de acesso concorrente de múltiplos clientes HTTP, cenário em que o Postgres é mais maduro |
| **Ler CSV com pandas em memória** | 22MB por processo, recarregado a cada restart; sem índice, sem join eficiente, sem concorrência |
| **`INSERT` em lote (`executemany`)** | Funciona, mas ~10x mais lento que `COPY` sem ganho algum |
| **Descartar as linhas com ID duplicado** | **Perderia 38 mil registros clínicos reais.** Inaceitável |
| **Usar ID composto (`id` + `data` + `pessoa`) como PK** | Frágil: nada garante unicidade dessa combinação, e encadearia a chave em toda FK |

## 4. Consequências

### 4.1 Positivas

- **Carga em ~20s**, tornando `--recriar` parte normal do fluxo de desenvolvimento
- **Timeline de um paciente em 0,24ms** (medido com `EXPLAIN ANALYZE` no paciente
  736, o de maior volume: 2.486 exames)
- Schema criado automaticamente na primeira subida — sem passo manual
- Views deixam os filtros de qualidade **auditáveis** em vez de escondidos
- Validação pós-carga impede que o ambiente fique silenciosamente errado

### 4.2 Negativas e riscos

| Risco | Severidade | Mitigação |
|---|---|---|
| Nas 3 tabelas com chave substituta, o **ID original não identifica uma linha** | **Alta** — erro fácil e silencioso | Documentado no schema SQL, no README do banco e aqui. Joins devem usar `pk`. Um `JOIN ON id_exame` produz produto cartesiano parcial sem erro algum |
| **Duas fontes de schema** — este SQL de bootstrap e as migrations Alembic (ADR-006) | **Alta** | Teste no CI comparando o schema das migrations com o produzido por `01_schema.sql` |
| `exame` ocupa **44MB** com índices (banco total: 75MB) | Baixa | Dentro do razoável. Índices em `nome_exame` e `data` justificam o custo |
| Volume Docker pode ser apagado por `down -v` | Baixa | Recarga é um comando. Nenhum dado é exclusivo do banco |
| `POSTGRES_INITDB_ARGS` com `--locale=C` | Baixa | Escolhido para evitar custo de reindexação por locale. Ordenação de texto acentuado segue bytes, não regra do português — relevante se houver `ORDER BY nome` |

### 4.3 Impacto em quem implementa

**Ao consultar `exame`, `exposicao_medicamento` ou `observacao`:**
```sql
-- ERRADO: id_exame não é único, isto duplica linhas
SELECT * FROM exame e JOIN outra o ON o.ref = e.id_exame;

-- CORRETO: pk é a identidade real
SELECT * FROM exame e WHERE e.pk = :pk;
```

No ORM, `pk` é a primary key declarada; o ID original é coluna indexada sem
unicidade (ADR-006).

**Ao consultar medicamentos:** use `vw_medicamento_valido` (mapeada como modelo
`MedicamentoValido`), nunca `exposicao_medicamento` direto — ou 26,8% do
resultado será diagnóstico rotulado como fármaco.

**Ao mudar o schema:** edite `Data/DB/sql/01_schema.sql`, gere a migration
Alembic correspondente (ADR-006) e rode
`python3 Data/DB/scripts/popular_banco.py --recriar`. As duas fontes precisam
concordar. Editar a tabela no psql deixa o ambiente divergente do versionado.

**Ao adicionar uma query no caminho crítico:** rode `EXPLAIN ANALYZE`. Os
índices cobrem filtro por `id_pessoa`, `id_atendimento`, `nome_*` e data; um
filtro em coluna não indexada varre até 199 mil linhas.

## 5. Gatilhos de revisão

- O banco passar a **receber escrita** da aplicação → transações e unit of work
- Volume crescer em **ordem de magnitude** (>3M linhas) → particionamento de `exame`
- Necessidade de **múltiplos ambientes** simultâneos → schema por ambiente
- Dataset **regerado** com IDs corrigidos → a chave substituta pode ser removida

## 6. Referências

- `Data/DB/README.md` · `Data/DB/sql/01_schema.sql` · `Data/DB/scripts/popular_banco.py`
- ADR-001 (dataset), ADR-003 (`.env`), ADR-006 (ORM e migrations), ADR-008 (limitações)
