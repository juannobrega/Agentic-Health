# ADR-004 BACKEND EM FASTAPI

| | |
|---|---|
| **Status** | Aceita |
| **Data** | 2026-10-02 |
| **Impacto** | Toda a camada de serviço; contrato com o frontend |
| **Depende de** | ADR-002 |

---

## 1. Contexto

O backend precisa expor prontuário, atendimentos, coortes e estatísticas. Três
requisitos moldam a escolha do framework:

1. **O schema da API precisa ser legível por máquina.** O frontend gera seus
   tipos TypeScript a partir do contrato (ADR-007). Um contrato escrito à mão em
   Markdown divergiria do código.

2. **Tipos validados nas respostas.** O dataset tem campos que são nulos por
   limitação estrutural (`valor_numerico` em 100% dos exames), FKs opcionais e
   datas que podem faltar. Serializar isso à mão produz bugs sutis — um `None`
   virando string `"None"` no JSON.

3. **Mesma linguagem do resto do projeto.** O script de carga é Python; manter
   um só ecossistema reduz a carga cognitiva e permite reusar o conhecimento do
   schema.

## 2. Decisão

**FastAPI + Pydantic v2**, Python 3.12+, servido por Uvicorn como serviço no
mesmo `docker-compose.yml`. Código em `api/` na raiz.

### 2.1 Estrutura proposta

```
api/
├── Dockerfile
├── requirements.txt
├── main.py                    app, lifespan, CORS, middleware
├── config.py                  leitura do .env da raiz (ADR-003)
├── db.py                      engine e sessão SQLAlchemy (ADR-006)
├── modelos/                   SQLAlchemy ORM — forma do banco
├── esquemas/                  Pydantic — forma da API
├── repositorios/              acesso a dados (ADR-006)
│   ├── paciente.py
│   ├── atendimento.py
│   ├── coorte.py
│   └── analitico.py           SQL direto nas consultas analíticas
├── migrations/                Alembic
└── routers/                   rotas por domínio
    ├── pacientes.py
    ├── atendimentos.py
    ├── coortes.py
    ├── estatisticas.py
    └── dicionario.py
```

Separação deliberada entre `repositorios/` e `routers/`: o acesso a dados fica
testável sem subir a aplicação HTTP, e um repositório serve múltiplas rotas.
`modelos/` e `esquemas/` são separados de propósito — ver ADR-006.

### 2.2 Por que o OpenAPI importa tanto aqui

FastAPI gera o OpenAPI a partir das assinaturas e dos modelos Pydantic. Esse
documento serve **três consumidores sem trabalho extra**:

| Consumidor | Uso |
|---|---|
| Frontend | Geração de tipos TypeScript (ADR-007) |
| Desenvolvedor | `/docs` interativo para explorar a API |

Uma fonte, dois usos. Com um framework sem OpenAPI, ambos exigiriam manutenção
manual e divergiriam.

### 2.3 Pool de conexões

O engine async do SQLAlchemy (ADR-006) é criado no `lifespan` da aplicação, com
`pool_size=5, max_overflow=5`. Sem pool, cada request pagaria o handshake de
conexão do Postgres (~5ms) — mais que o tempo da própria query (0,24ms medidos
na timeline).

### 2.4 Tratamento dos nulos estruturais

Os modelos Pydantic declaram explicitamente o que pode ser nulo e **por quê**:

```python
class ExameResposta(BaseModel):
    nome_exame: str
    data: date
    valor_numerico: float | None = Field(
        default=None,
        description="Sempre nulo neste dataset: os resultados se perderam "
                    "no ETL do Synthea. Ver ADR-008.",
    )
```

A descrição entra no OpenAPI e chega ao frontend — a limitação viaja junto com o
dado (ADR-008).

## 3. Alternativas descartadas

| Alternativa | Por que não |
|---|---|
| **Flask** | Sem OpenAPI nativo nem validação de tipos; exigiria Marshmallow + apispec para chegar ao mesmo lugar, com mais peças |
| **Django + DRF** | ORM e admin são o ponto forte do Django, e não usamos nenhum dos dois (ADR-006). Peso desproporcional para uma API somente leitura |
| **Node/Express** | Introduziria um segundo ecossistema no backend. O frontend já é TypeScript (ADR-007), mas compartilhar linguagem com o script de carga vale mais aqui |
| **Node/NestJS** | Mesmo ponto, com mais estrutura do que o escopo justifica |
| **Go** | Performance excelente e binário único, mas o gargalo aqui é I/O de banco, não CPU. Perderia o compartilhamento com o script de carga |
| **GraphQL** | Atraente para a timeline (cliente escolhe os campos). Descartado porque o conjunto de consultas é conhecido e estável, e o OpenAPI já gera os tipos do frontend sem camada extra |

## 4. Consequências

### 4.1 Positivas

- **OpenAPI de graça**, servindo a geração de tipos do frontend e a documentação
- Pydantic **valida e documenta** cada campo, inclusive os nulos estruturais
- `/docs` interativo acelera o desenvolvimento e serve de ferramenta de exploração
- Async nativo: requests concorrentes não bloqueiam entre si durante I/O de banco
- Um só ecossistema com o script de carga

### 4.2 Negativas e riscos

| Risco | Severidade | Mitigação |
|---|---|---|
| **Handler bloqueante degrada todo o event loop** | **Alta** | psycopg 3 em modo async; qualquer operação CPU-bound vai para `run_in_executor`. Code review atento a `time.sleep`, requests sincronizados e parsing pesado |
| Pydantic v2 tem **API diferente da v1** | Média | Fixar a versão no `requirements.txt`; não copiar validadores de exemplos v1 |
| Esquemas Pydantic **duplicam os modelos ORM** | Baixa | Duplicação intencional (ADR-006): formas diferentes com propósitos diferentes |
| OpenAPI mal descrito **engana o frontend** | Média | Toda limitação de dado vai na `description` do campo (ADR-008) |
| Pool mal dimensionado sob carga | Baixa | `max_size=10` contra o default de 100 conexões do Postgres deixa folga ampla |

### 4.3 Impacto em quem implementa

**Nunca bloqueie o event loop.** Esta é a armadilha número um:
```python
# ERRADO — trava todos os requests concorrentes
@router.get("/pacientes")
def listar(sessao: Session):
    return sessao.scalars(stmt).all()        # driver síncrono

# CORRETO
@router.get("/pacientes")
async def listar(sessao: AsyncSession = Depends(get_sessao)):
    return (await sessao.scalars(stmt)).all()
```

**Toda `description` de campo é contrato**, não comentário. O frontend lê o
OpenAPI para gerar tipos; um campo sem descrição de limitação vira bug de
interpretação a jusante.

**Modelos de resposta sempre explícitos.** Nunca retorne o dict cru do banco:
sem modelo, o OpenAPI fica vazio e os dois consumidores a jusante quebram.

**Paginação obrigatória em qualquer lista.** Um paciente tem até 2.486 exames; a
base tem 199.514. Retornar lista sem limite é um incidente esperando acontecer.

## 5. Gatilhos de revisão

- API precisar de **escrita** → transações, idempotência, validação de entrada
- Latência de **CPU** se tornar gargalo (hoje é I/O) → reavaliar runtime
- Necessidade de **subscrições/tempo real** → WebSocket ou SSE
- Múltiplos clientes com necessidades divergentes de campo → reconsiderar GraphQL

## 6. Referências

- ADR-002 (banco), ADR-003 (`.env`), ADR-006 (ORM), ADR-007 (frontend)
- [FastAPI](https://fastapi.tiangolo.com) · [Pydantic v2](https://docs.pydantic.dev)
