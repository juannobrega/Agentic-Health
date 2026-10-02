# E5 PLATAFORMA E QUALIDADE

Infraestrutura para API e frontend subirem, e as garantias de que continuam corretos.

**Implementar primeiro** — as demais HUs dependem disto.

6 HUs

---

## HU-5.1 SUBIR A API NO DOCKER COMPOSE `MUST`

**Como** engenheiro, **quero** subir a API junto do banco com um comando,
**para** ter o ambiente completo sem passos manuais.

### Critérios de aceite

- [ ] Serviço `api` no `docker-compose.yml` da raiz
- [ ] Dockerfile multi-stage, imagem final enxuta
- [ ] Credenciais vindas do **`.env` da raiz** (ADR-003)
- [ ] `POSTGRES_HOST=postgres` dentro do compose, não `localhost`
- [ ] `depends_on` com `condition: service_healthy` — a API só sobe após o banco
- [ ] Healthcheck próprio em `GET /saude`
- [ ] Hot-reload em desenvolvimento (volume montado + `--reload`)
- [ ] `docker compose up -d` sobe banco e API funcionando

### Armadilhas
`POSTGRES_HOST=localhost` dentro de um container aponta para o próprio
container — é o erro mais provável desta HU (ADR-003).

O `.env` da raiz só é lido porque o compose está na raiz. Não mova o compose.

### Dependências
ADR-003, ADR-004

---

## HU-5.2 SUBIR O FRONTEND NO DOCKER COMPOSE `MUST`

**Como** engenheiro, **quero** subir o frontend junto,
**para** ter o stack completo rodando.

### Critérios de aceite

- [ ] Serviço `web` no `docker-compose.yml`
- [ ] Dockerfile multi-stage: build com Node, serve estático
- [ ] URL da API vinda do `.env` da raiz
- [ ] CORS configurado na API para a origem do frontend
- [ ] Hot-reload em desenvolvimento
- [ ] `docker compose up -d` sobe banco, API e frontend

### Armadilhas
CORS é a falha mais comum na integração: a API precisa permitir explicitamente a
origem do frontend (ADR-005 — sem auth, mas CORS restrito).

### Dependências
HU-5.1 · ADR-007

---

## HU-5.3 GERAR OS TIPOS TYPESCRIPT DO OPENAPI `MUST`

**Como** engenheiro, **quero** os tipos do frontend derivados do OpenAPI,
**para** que mudanças de contrato falhem no build.

### Critérios de aceite

- [ ] Script `npm run tipos` gera `web/src/api/tipos.ts` do OpenAPI
- [ ] Arquivo gerado marcado como **não editar à mão**
- [ ] Verificação no CI que **falha** se o arquivo divergir do OpenAPI atual
- [ ] Documentado no README do frontend

### Armadilhas
O risco é o arquivo ficar obsoleto porque ninguém regenerou (ADR-007). A
verificação no CI é o que transforma a intenção em garantia.

### Dependências
HU-5.1, HU-5.2 · ADR-007

---

## HU-5.4 MODELOS ORM E MIGRATIONS `MUST`

**Como** engenheiro, **quero** os modelos SQLAlchemy e as migrations Alembic,
**para** ter acesso a dados tipado e schema versionado.

### Critérios de aceite

- [ ] Modelos SQLAlchemy 2.0 (estilo `Mapped[...]`) para as 11 tabelas
- [ ] As 3 views mapeadas como entidade somente leitura
- [ ] Em `exame`, `exposicao_medicamento` e `observacao`, **`pk` é a primary
      key**; o ID original é coluna indexada **sem** unicidade
- [ ] Relacionamentos com `lazy="raise"` — acesso não carregado levanta erro
- [ ] Alembic configurado com `include_schemas=True` e **exclusão de views** no
      autogenerate
- [ ] Migration inicial reproduz o schema atual de `Data/DB/sql/01_schema.sql`
- [ ] Engine async com `pool_size=5, max_overflow=5`, criado no `lifespan`
- [ ] Sessão como dependência do FastAPI, fechada ao fim do request

### Armadilhas
**O erro crítico:** declarar `id_exame` como `primary_key=True`. O SQLAlchemy
trataria as 29.471 linhas com ID repetido como a mesma entidade — corrupção
silenciosa na sessão de identidade (ADR-006).

Sem `lazy="raise"`, uma travessia de relacionamento numa lista de 25 pacientes
emite 25 queries extras sem ninguém notar.

Alembic sem filtro de view tenta criar `vw_medicamento_valido` como tabela.

### Dependências
HU-5.1, HU-5.4 · ADR-002, ADR-006

---

## HU-5.5 TESTES DE CONTRATO E DE SCHEMA `MUST`

**Como** engenheiro, **quero** testes que peguem divergência de schema e falhas
de segurança, **para** não descobrir em produção.

### Critérios de aceite

- [ ] Teste que **compara o schema gerado pelas migrations** com o produzido por
      `Data/DB/sql/01_schema.sql` — divergência **falha o build**
- [ ] Teste que falha se `id_exame`, `id_exposicao_medicamento` ou
      `id_observacao` for declarado como primary key
- [ ] Teste de **injection** nos filtros dinâmicos de coorte
- [ ] Teste de **N+1**: conta as queries emitidas nas travessias de relacionamento
- [ ] Teste das premissas do dataset: exames sem valor (0), medicamentos
      excluídos (7.899), pacientes válidos (1.128)
- [ ] Cada consulta analítica em SQL direto tem teste contra o banco real
- [ ] Suíte roda no CI contra um banco carregado

### Armadilhas
**Duas fontes de schema** — o SQL de bootstrap do initdb e as migrations Alembic
(ADR-002, ADR-006). O teste de comparação é o que impede a divergência, e é o
risco mais provável do projeto.

### Dependências
HU-5.4 · ADR-002, ADR-006

---

## HU-5.6 VALIDACAO DO AMBIENTE `SHOULD`

**Como** engenheiro, **quero** verificar que o ambiente está correto,
**para** diagnosticar problemas rápido.

### Critérios de aceite

- [ ] `GET /saude` retorna status da API e conectividade com o banco
- [ ] `GET /saude/dados` confere as contagens esperadas das 11 tabelas
- [ ] Endpoint informa se o banco está vazio, parcialmente ou totalmente carregado
- [ ] Reusa a lógica de validação de `popular_banco.py --verificar`
- [ ] Informa a revisão atual do Alembic e se há migration pendente
- [ ] README da raiz documenta o fluxo completo de setup

### Armadilhas
Um banco parcialmente carregado é pior que vazio: as telas funcionam, mas os
números estão errados. Este endpoint existe para detectar isso.

### Dependências
HU-5.1, HU-5.4 · ADR-002
