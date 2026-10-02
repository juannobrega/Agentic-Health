# ADR-006 SQLALCHEMY COM SQL NAS ANALITICAS

| | |
|---|---|
| **Status** | Aceita |
| **Data** | 2026-10-02 |
| **Impacto** | Toda a camada de acesso a dados |
| **Depende de** | ADR-002, ADR-004 |
| **Substitui** | Versão anterior desta ADR, que decidia por SQL direto sem ORM |

---

## 1. Contexto

A camada de acesso a dados precisa atender dois tipos de consulta bem diferentes.

### 1.1 Consultas de entidade e relacionamento

A maior parte da API: obter um paciente, listar seus atendimentos, navegar do
atendimento para as condições diagnosticadas nele. São travessias de
relacionamento, repetitivas e previsíveis.

Escritas em SQL cru, cada uma exige mapear colunas à mão, repetir o `JOIN` e
converter o resultado — trabalho mecânico que erra em silêncio quando o schema muda.

### 1.2 Consultas analíticas

Um conjunto menor, mas central ao produto:

- **Timeline** — `UNION ALL` de 4 domínios (condição, medicamento, procedimento,
  exame) ordenado por data
- **Prevalência** — `count(DISTINCT id_pessoa)` com corte demográfico
- **Multimorbidade** — `HAVING count(DISTINCT nome_condicao) >= 2`
- **Trajetória** — CTE recursiva sobre `id_atendimento_anterior`

Essas são naturais em SQL e verbosas em qualquer ORM.

### 1.3 Filtros dinâmicos: onde o risco se concentra

O construtor de coortes (HU-3.3) combina até 6 filtros opcionais sobre condição,
medicamento, idade, sexo, raça e tipo de atendimento. Montar `WHERE` dinâmico
por concatenação de string é **a principal superfície de SQL injection** do
projeto, e a disciplina humana é uma barreira frágil.

### 1.4 Particularidades do schema que o ORM precisa respeitar

| Particularidade | Exigência |
|---|---|
| **Chave substituta `pk`** em 3 tabelas (ADR-002) | O modelo deve declarar `pk` como PK, **não** o ID original |
| **`0` como sentinela** de FK ausente | Convertido para `NULL` na carga; relacionamentos ficam opcionais |
| **Views de qualidade** (`vw_medicamento_valido`) | Mapeadas como entidade somente leitura |
| **83% de `concept_id = 0`** em observação | Filtrar por `nome_*`, não por conceito |

## 2. Decisão

**SQLAlchemy 2.0** como ORM, com **Alembic** para migrations. SQL direto —
via `text()` ou SQLAlchemy Core — nas consultas analíticas.

### 2.1 Divisão de responsabilidade

| Tipo de consulta | Ferramenta | Por quê |
|---|---|---|
| Obter entidade por ID | ORM | Mapeamento automático, relacionamentos |
| Listar com filtros opcionais | ORM (`select()` + `where()` condicional) | Composição segura, sem injection |
| Navegar relacionamento | ORM (`selectinload`) | Evita N+1 declarativamente |
| Coorte com filtros dinâmicos | ORM | **Elimina o risco de injection** |
| Timeline (`UNION ALL` de 4 domínios) | SQL direto | Mais legível que o equivalente em ORM |
| Agregações e prevalência | SQL direto | `count(DISTINCT)` + `HAVING` são mais claros em SQL |
| Trajetória (CTE recursiva) | SQL direto | Recursão é desajeitada no ORM |

A regra: **ORM por padrão; SQL quando o SQL for mais claro.** Não o contrário.

### 2.2 Estrutura

```
api/
├── modelos/              SQLAlchemy ORM (tabelas e views)
│   ├── base.py
│   ├── pessoa.py
│   ├── atendimento.py
│   ├── clinico.py        condicao, medicamento, procedimento, exame, observacao
│   └── views.py          vw_medicamento_valido, vw_pessoa_valida
├── repositorios/         acesso a dados
│   ├── paciente.py       ORM
│   ├── atendimento.py    ORM
│   ├── coorte.py         ORM — filtros dinâmicos
│   └── analitico.py      SQL direto — timeline, estatísticas, trajetória
├── esquemas/             Pydantic (resposta da API)
└── migrations/           Alembic
```

Separação deliberada entre `modelos/` (ORM, forma do banco) e `esquemas/`
(Pydantic, forma da API). Não são a mesma coisa: a API expõe `idade` calculada,
oculta colunas internas e marca campos indisponíveis (ADR-008).

### 2.3 Chave substituta no modelo

**O ponto mais fácil de errar.** Nas três tabelas afetadas, o ID original
**não** é a primary key:

```python
class Exame(Base):
    __tablename__ = "exame"
    __table_args__ = {"schema": "synthea"}

    # PK real: chave substituta gerada na carga (ADR-002)
    pk: Mapped[int] = mapped_column(primary_key=True)

    # ID do dataset: NAO e unico — 29.471 valores repetidos.
    # Indexado para lookup, sem constraint de unicidade.
    id_exame: Mapped[int] = mapped_column(index=True)

    id_pessoa: Mapped[int] = mapped_column(ForeignKey("synthea.pessoa.id_pessoa"))
    nome_exame: Mapped[str | None]
    valor_numerico: Mapped[Decimal | None]   # sempre NULL neste dataset (ADR-008)
```

Declarar `id_exame` como `primary_key=True` faria o SQLAlchemy tratar linhas
distintas como a mesma entidade — corrupção silenciosa na sessão de identidade.

### 2.4 Views como entidade somente leitura

```python
class MedicamentoValido(Base):
    """View que exclui os 7.899 registros com codigo SNOMED de condicao (ADR-008)."""
    __tablename__ = "vw_medicamento_valido"
    __table_args__ = {"schema": "synthea", "info": {"is_view": True}}

    pk: Mapped[int] = mapped_column(primary_key=True)
    id_pessoa: Mapped[int]
    nome_medicamento: Mapped[str | None]
```

Alembic deve **ignorar** views no autogenerate (`include_object`), senão tenta
criá-las como tabela.

### 2.5 Filtros dinâmicos sem risco

O ganho mais concreto do ORM neste projeto:

```python
async def buscar(sessao, sexo=None, idade_min=None, condicoes=None):
    stmt = select(PessoaValida)

    if sexo:
        stmt = stmt.where(PessoaValida.sexo == sexo)
    if idade_min is not None:
        stmt = stmt.where(PessoaValida.idade >= idade_min)
    if condicoes:
        stmt = stmt.where(
            PessoaValida.id_pessoa.in_(
                select(Condicao.id_pessoa).where(Condicao.nome_condicao.in_(condicoes))
            )
        )

    return (await sessao.scalars(stmt)).all()
```

Sem concatenação de string, sem risco de injection, e a ordenação dinâmica usa
atributo do modelo em vez de nome de coluna vindo do cliente.

### 2.6 SQL direto nas analíticas

Quando o SQL é mais claro, ele fica explícito e parametrizado:

```python
TIMELINE = text("""
    SELECT 'condicao' AS tipo, data_inicio AS data, nome_condicao AS nome, pk
      FROM synthea.condicao             WHERE id_pessoa = :id_pessoa
    UNION ALL
    SELECT 'exame', data, nome_exame, pk
      FROM synthea.exame                WHERE id_pessoa = :id_pessoa
    UNION ALL
    SELECT 'medicamento', data_inicio, nome_medicamento, pk
      FROM synthea.vw_medicamento_valido WHERE id_pessoa = :id_pessoa
    UNION ALL
    SELECT 'procedimento', data, nome_procedimento, pk
      FROM synthea.procedimento         WHERE id_pessoa = :id_pessoa
    ORDER BY data DESC
    LIMIT :limite OFFSET :deslocamento
""")
```

Parâmetros nomeados (`:id_pessoa`), nunca f-string.

### 2.7 Migrations com Alembic

O banco é criado hoje por `Data/DB/sql/01_schema.sql` executado no initdb
(ADR-002). Com Alembic, o schema passa a ter histórico versionado:

- A migration inicial reproduz o schema atual
- Os arquivos em `Data/DB/sql/` permanecem como **caminho de bootstrap** do
  container, e precisam ser mantidos em sincronia com as migrations
- Alembic configurado com `include_schemas=True` e exclusão de views

**Risco assumido:** duas fontes de schema (SQL do initdb e migrations). Mitigação
na seção 4.2.

## 3. Alternativas descartadas

| Alternativa | Por que não |
|---|---|
| **SQL direto sem ORM** (decisão anterior) | Nenhuma proteção contra injection nos filtros dinâmicos de coorte; mapeamento manual repetitivo; divergência schema/modelo invisível até runtime |
| **SQLModel** | Unifica modelo ORM e Pydantic, reduzindo duplicação — atraente. Recusado porque abstrai o SQLAlchemy de forma que atrapalha em consultas analíticas, e porque misturar a forma do banco com a forma da API é indesejável aqui (a API expõe `idade` calculada e campos marcados como indisponíveis) |
| **Tortoise ORM** | Async-first e sintaxe agradável, mas ecossistema menor e suporte a views, CTE e SQL analítico menos maduro |
| **ORM para absolutamente tudo** | A timeline em ORM seria um `union_all()` de 4 `select()` com labels alinhados à mão — mais verboso e menos legível que o SQL. Nenhum ganho de segurança, já que não há filtro dinâmico ali |
| **Peewee** | Mais simples, mas sem async maduro — bloquearia o event loop (ADR-004) |
| **Prisma (Python)** | Schema próprio conflitaria com o SQL versionado e o Alembic |

## 4. Consequências

### 4.1 Positivas

- **Injection eliminada** nos filtros dinâmicos de coorte, a maior superfície de
  risco do projeto
- Mapeamento automático: menos código mecânico, menos erro de conversão
- **Migrations versionadas** — o schema passa a ter histórico e caminho de evolução
- `selectinload` resolve N+1 declarativamente nas travessias de relacionamento
- Tipagem estática do SQLAlchemy 2.0 (`Mapped[...]`) pega erro de campo no editor
- SQL preservado onde é mais claro: timeline, agregações e trajetória seguem legíveis

### 4.2 Negativas e riscos

| Risco | Severidade | Mitigação |
|---|---|---|
| **Chave substituta mal declarada** no modelo | **Crítica** | Comentário explícito em cada um dos 3 modelos; teste que falha se `id_exame`/`id_exposicao_medicamento`/`id_observacao` for declarado como PK |
| **Duas fontes de schema**: SQL do initdb + migrations | **Alta** | Teste no CI que compara o schema gerado pelas migrations com o produzido por `01_schema.sql`. Divergência falha o build |
| **N+1 silencioso** em travessia de relacionamento | **Alta** | `lazy="raise"` nos relacionamentos: acesso não carregado explicitamente levanta erro em vez de emitir query extra |
| ORM esconde o custo real da query | Média | `echo=True` em desenvolvimento; `EXPLAIN ANALYZE` nas consultas do caminho crítico |
| Sessão async mal gerenciada vaza conexão | Média | `async_sessionmaker` com dependência do FastAPI que fecha a sessão no fim do request |
| Alembic autogenerate tenta criar as **views** como tabela | Média | `include_object` filtrando `info={"is_view": True}` |
| Curva do SQLAlchemy 2.0 — API bem diferente da 1.x | Baixa | Usar só o estilo 2.0 (`select()`, `Mapped[]`); não copiar exemplos 1.x |
| Modelos ORM e esquemas Pydantic duplicam campos | Baixa | Duplicação intencional: formas diferentes com propósitos diferentes |

### 4.3 Impacto em quem implementa

**Nas três tabelas com duplicata, a PK é `pk`.** Nunca declare o ID original como
primary key:
```python
# ERRADO — SQLAlchemy tratará linhas distintas como a mesma entidade
class Exame(Base):
    id_exame: Mapped[int] = mapped_column(primary_key=True)

# CORRETO
class Exame(Base):
    pk: Mapped[int] = mapped_column(primary_key=True)
    id_exame: Mapped[int] = mapped_column(index=True)   # NAO unico
```

**Use a view, não a tabela, para medicamentos:**
```python
# ERRADO — inclui 7.899 diagnósticos rotulados como fármaco
select(ExposicaoMedicamento).where(ExposicaoMedicamento.id_pessoa == id)

# CORRETO
select(MedicamentoValido).where(MedicamentoValido.id_pessoa == id)
```

**Carregue relacionamento explicitamente.** Com `lazy="raise"`, esquecer disso
levanta erro em desenvolvimento — melhor que N+1 em produção:
```python
select(Atendimento).options(selectinload(Atendimento.condicoes))
```

**Ordenação dinâmica por atributo do modelo**, nunca por string do cliente:
```python
ORDENAVEIS = {"id_pessoa": PessoaValida.id_pessoa, "idade": PessoaValida.idade}
coluna = ORDENAVEIS.get(ordenar_por)
if coluna is None:
    raise HTTPException(400, "coluna de ordenação inválida")
```

**SQL direto sempre com parâmetro nomeado.** Se você está escrevendo f-string
com SQL, pare.

**Ao mudar o schema:** gere a migration **e** atualize `Data/DB/sql/01_schema.sql`.
As duas fontes precisam concordar — é o risco mais provável desta ADR.

**Sempre `LIMIT`.** Nenhuma consulta de lista sem paginação (199.514 exames).

## 5. Gatilhos de revisão

- Consultas analíticas crescerem ao ponto de `analitico.py` ficar difícil de
  manter → avaliar views materializadas no banco
- Divergência entre SQL do initdb e migrations causar **incidente** → eliminar o
  SQL de bootstrap e criar o schema só por Alembic
- Perda de performance atribuível ao ORM → medir e mover a consulta para SQL direto
- API passar a **escrever** → aproveitar unit of work e transações do ORM

## 6. Referências

- ADR-002 (schema, chave substituta e views), ADR-004 (backend), ADR-008 (filtros)
- [SQLAlchemy 2.0](https://docs.sqlalchemy.org/en/20/) · [Alembic](https://alembic.sqlalchemy.org)
