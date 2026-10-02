# ADR-003 ENV UNICO NA RAIZ

| | |
|---|---|
| **Status** | Aceita |
| **Data** | 2026-10-02 |
| **Impacto** | Setup de ambiente, todos os serviços |
| **Depende de** | ADR-002 |

---

## 1. Contexto

Banco, backend e frontend precisam das mesmas credenciais de conexão. A opção
natural — um `.env` por serviço — leva a **divergência silenciosa**: a senha
muda em um arquivo, o outro serviço continua com a antiga e falha com erro de
autenticação que não aponta para a causa.

Havia um `.env` em `Data/DB/` quando o `docker-compose.yml` morava lá.

### 1.1 O problema que descobrimos

O `docker compose` só lê automaticamente o `.env` que está **no mesmo diretório
do arquivo compose**. Com o compose em `Data/DB/`, um `.env` na raiz era
**ignorado sem aviso**: o Compose caía nos valores default das expressões
`${VAR:-default}` e subia o container com credenciais diferentes das
configuradas.

Isto foi verificado empiricamente. Com `POSTGRES_PORT=5499` no `.env` da raiz:

```
$ docker compose config | grep published
        published: "5432"      ← ignorou o .env, usou o default
```

Falha especialmente perigosa porque **não produz erro** — o ambiente sobe
"funcionando", só não com a configuração pedida.

### 1.2 Primeira tentativa, descartada

Criamos um `Makefile` que passava `--env-file "$(CURDIR)/.env"` em todos os
alvos. Funcionou, mas introduziu uma camada de indireção só para contornar um
problema de layout de arquivos — e exigia que todo comando passasse pelo `make`.
Foi removido em favor da solução direta.

## 2. Decisão

**Um único `.env` na raiz do projeto**, fonte de verdade para todos os serviços.
O `docker-compose.yml` foi **movido para a raiz**, onde o Compose lê o `.env`
ao lado nativamente.

### 2.1 Como cada consumidor lê

| Consumidor | Mecanismo |
|---|---|
| `docker compose` | Lê `.env` do próprio diretório automaticamente — sem flag |
| Serviços no container | Recebem as variáveis via `environment:` no compose |
| Scripts Python | `load_dotenv(Path(__file__).resolve().parents[3] / ".env")` |

### 2.2 Variáveis

```bash
POSTGRES_DB=agentic_health
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_PORT=5432
POSTGRES_HOST=localhost   # 'postgres' dentro do compose
```

`POSTGRES_HOST` merece atenção: scripts na máquina usam `localhost`, mas um
serviço **dentro** do compose precisa do nome do serviço (`postgres`) para
resolver pela rede interna do Docker.

### 2.3 Verificação

Com o compose na raiz, o mesmo teste agora passa:

```
$ docker compose config | grep published
        published: "5499"      ← leu o .env da raiz
```

Validado end-to-end: subida, carga das 312.276 linhas pela porta customizada, e
retorno ao padrão.

## 3. Alternativas descartadas

| Alternativa | Por que não |
|---|---|
| **`.env` por serviço** | Divergência silenciosa de credenciais — o problema que motivou esta ADR |
| **Makefile com `--env-file`** | Implementado e removido: indireção desnecessária para resolver um problema de layout |
| **`env_file:` no compose** | Injeta variáveis **no container**, mas não resolve a interpolação de `${...}` nas seções `ports`/`volumes` do próprio compose. Resolve metade do problema |
| **Compose em `Data/DB` + sempre passar `--env-file`** | Depende de disciplina humana; esquecer a flag volta ao bug silencioso |
| **Variáveis de ambiente do shell** | Não versionável, não documentável, perde-se entre sessões |

## 4. Consequências

### 4.1 Positivas

- **Uma credencial, um lugar.** Impossível divergir entre serviços.
- `docker compose up -d` funciona **sem flag nem wrapper**
- `.env.example` versionado documenta todas as variáveis; `.env` fica no gitignore
- Novos serviços (API, frontend) herdam a configuração sem arquivo próprio

### 4.2 Negativas e riscos

| Risco | Severidade | Mitigação |
|---|---|---|
| Compose na raiz referencia **caminhos de subpasta** (`./Data/DB/sql`) | Baixa | Acoplamento aceito; mover `Data/DB` exige editar o compose |
| Scripts usam **`parents[3]`** para achar a raiz | Média | Quebra se a árvore de diretórios mudar. Um helper centralizado reduziria o risco se mais scripts aparecerem |
| **Um arquivo para todos os serviços** cresce com o projeto | Baixa | Organizar em seções comentadas por serviço |
| Secrets em texto plano no `.env` | Média | Aceitável com dados sintéticos e sem auth (ADR-005). Com dados reais, usar gerenciador de secrets |
| Dev pode usar `docker compose` de dentro de `Data/DB` por hábito | Média | Não há mais compose lá, então falha explicitamente — melhor que falhar em silêncio |

### 4.3 Impacto em quem implementa

**Sempre rode o compose da raiz:**
```bash
cd "Agentic Health" && docker compose up -d
```

**Ao adicionar um serviço ao compose,** use `${VAR:-default}` e documente a
variável no `.env.example`. Nunca hardcode credencial no YAML.

**Ao escrever um script que precise do banco,** carregue o `.env` da raiz
explicitamente — não confie no diretório de trabalho:
```python
_RAIZ = Path(__file__).resolve().parents[3]
load_dotenv(_RAIZ / ".env")
```

**Dentro do compose, `POSTGRES_HOST` é `postgres`, não `localhost`.** Este é o
erro mais provável ao conectar a API: `localhost` dentro de um container aponta
para o próprio container.

## 5. Gatilhos de revisão

- Projeto ganhar **múltiplos ambientes** (dev/staging/prod) → `.env.<ambiente>`
- Entrarem **secrets reais** (chave de API, dados de paciente) → gerenciador de secrets
- Deploy em **orquestrador** (Kubernetes) → ConfigMap/Secret em vez de `.env`
- Número de variáveis crescer ao ponto de confundir → separar por serviço com prefixo

## 6. Referências

- `.env.example` · `docker-compose.yml` · `Data/DB/scripts/popular_banco.py`
- ADR-002 (banco), ADR-005 (sem autenticação)
