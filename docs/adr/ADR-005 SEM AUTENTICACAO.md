# ADR-005 SEM AUTENTICACAO

| | |
|---|---|
| **Status** | Aceita |
| **Data** | 2026-10-02 |
| **Impacto** | Segurança, deploy, arquitetura de rotas |
| **Depende de** | ADR-001 |
| **Revisão obrigatória** | Antes de qualquer exposição pública ou uso de dado real |

---

## 1. Contexto

A API expõe prontuários completos: diagnósticos, medicamentos, procedimentos e
alergias por paciente. Em um sistema de saúde real isso exigiria:

- Autenticação de usuário
- Autorização por papel (médico vê seus pacientes; pesquisador vê agregados)
- Trilha de auditoria de acesso — quem viu qual prontuário e quando
- Conformidade com LGPD (Brasil) e, se houver dado americano, HIPAA
- Consentimento e política de retenção

**Os dados aqui são 100% sintéticos** (ADR-001). Nenhum dos 1.130 "pacientes"
corresponde a pessoa real: foram gerados por simulação a partir de dados
epidemiológicos agregados. Não existe dado pessoal a proteger, nem titular que
possa ser identificado ou prejudicado.

Implementar autenticação agora custaria: middleware de auth, modelo de usuário e
papel, fluxo de login/refresh no frontend, gestão de token, e testes para todos
esses caminhos. Protegeria exatamente ninguém.

## 2. Decisão

**Nenhuma autenticação ou autorização.** Todos os endpoints são públicos para
quem alcança a rede onde a API roda.

Decisão **explícita e condicional**: válida enquanto os dados forem sintéticos e
a API não estiver exposta fora de rede local.

### 2.1 O que isso NÃO significa

Esta decisão não dispensa as outras proteções. Continuam obrigatórias:

| Proteção | Por quê |
|---|---|
| **Consultas via ORM ou parametrizadas** | SQL injection não depende de autenticação (ADR-006) |
| **Validação de entrada** | Um parâmetro malformado não deve derrubar a API |
| **Paginação obrigatória** | Sem ela, um request pode esgotar memória |
| **CORS restrito** | Evita que qualquer página web consuma a API do navegador do usuário |
| **Timeout de query** | Impede que uma consulta pesada bloqueie o pool |

Ausência de auth é ausência de **identidade**, não licença para código frágil.

### 2.2 Restrição de deploy

A API deve rodar em `localhost` ou rede privada. Não há camada que impeça
leitura de qualquer prontuário por qualquer requisitante.

## 3. Alternativas descartadas

| Alternativa | Por que não |
|---|---|
| **OAuth2 / OIDC** | Peso e complexidade de provedor de identidade para proteger dados que não precisam de proteção |
| **JWT próprio** | Exigiria gestão de chave, expiração e refresh. Custo real, benefício zero com dado sintético |
| **API key estática** | Segurança teatral: uma chave compartilhada no frontend é pública na prática. Daria falsa sensação de proteção |
| **Basic auth** | Mesmo problema, com o agravante de credencial em cada request |
| **Auth só nos endpoints de paciente** | Inconsistência arbitrária: os endpoints de coorte também devolvem listas de pacientes |

Ponto comum entre as descartadas: todas adicionam complexidade **proporcional ao
código**, não ao risco. Com risco próximo de zero, qualquer custo é desproporcional.

## 4. Consequências

### 4.1 Positivas

- Frontend consome a API **sem fluxo de login**, token ou refresh — menos estado,
  menos telas, menos bugs
- `/docs` fica navegável para exploração livre
- Sem middleware de auth: menos superfície de código e de falha

### 4.2 Negativas e riscos

| Risco | Severidade | Mitigação |
|---|---|---|
| **API não pode ser exposta à internet** | **Crítica** se violada | Documentado aqui, no README e na ADR. Qualquer deploy público exige reabrir esta decisão primeiro |
| **Retrofit de auth vaza para toda a camada de rotas** | **Alta** | Mitigação parcial: manter as rotas finas e a lógica em `queries/`, para que a auth entre como dependência do FastAPI sem reescrever handlers |
| **Sem trilha de auditoria** — impossível saber quem viu o quê | Média | Aceito. Log de acesso HTTP registra IP e rota, mas não identidade |
| **Sem rate limiting** — cliente desatento satura o banco | Média | Paginação obrigatória e timeout de query limitam o dano de um request individual |
| Alguém assumir que o padrão é seguro e **copiar para projeto com dado real** | **Alta** | Esta ADR existe em grande parte para impedir isso. O gatilho de revisão é explícito |
| Dado sintético ser confundido com real | Média | ADR-009 (sem nomes fictícios) reduz esse risco diretamente |

### 4.3 Impacto em quem implementa

**Não assuma identidade de usuário em lugar nenhum.** Não há `request.user`.
Qualquer funcionalidade que dependa de "meus pacientes" ou "minhas coortes"
precisa de outro mecanismo — ou desta ADR revisada.

**Escreva o código como se a auth fosse chegar.** Rotas finas, lógica em
`repositorios/`, nenhuma regra de negócio no handler. Assim a auth entra como
dependência sem reescrita:
```python
# Preparado para receber auth depois sem mudar a assinatura
@router.get("/pacientes/{id}")
async def obter(id: int, sessao: AsyncSession = Depends(get_sessao)):
    return await repositorios.paciente.obter(sessao, id)
```

**Nunca faça deploy público.** Se precisar demonstrar externamente, use túnel
temporário com autenticação na camada do túnel — e trate como exceção consciente.

**CORS não é auth, mas configure-o.** Restringir a origem do frontend evita que
uma página arbitrária consuma a API pelo navegador de quem a acessa.

## 5. Gatilhos de revisão

Esta ADR **deve ser reaberta antes** de qualquer um destes:

| Gatilho | O que muda |
|---|---|
| Entrada de **dados reais de pacientes** | Auth, autorização, auditoria e conformidade LGPD passam a ser obrigatórios |
| Exposição **fora de rede local** | Auth obrigatória antes do deploy |
| **Múltiplos usuários** com papéis distintos | Modelo de usuário, RBAC e escopo por papel |
| Necessidade de **auditoria** de acesso | Identidade e log estruturado por usuário |
| Integração com **sistema externo** que exija identidade | Federação ou service account |

Nenhum destes é hipotético num projeto de saúde. A decisão é apropriada para
**agora** e tem data de validade implícita.

## 6. Referências

- ADR-001 (dados sintéticos), ADR-004 (backend), ADR-006 (ORM), ADR-009 (sem nomes)
- [LGPD — Lei 13.709/2018](https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709.htm)
