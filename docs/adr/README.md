# ARCHITECTURE DECISION RECORDS

Decisões de arquitetura do Agentic Health. Cada ADR registra o contexto que
levou à decisão, as alternativas descartadas **com o motivo**, as consequências
negativas e os gatilhos que obrigam a revisão.

## Índice

| # | Decisão | Status | Impacto |
|---|---|---|---|
| [ADR-001](ADR-001%20DATASET%20OMOP%20SINTETICO.md) | Dataset OMOP sintético como fonte única | Aceita | Todo o produto |
| [ADR-002](ADR-002%20POSTGRES%20EM%20DOCKER%20COM%20CARGA%20VIA%20COPY.md) | Postgres em Docker com carga via COPY | Aceita | Backend, performance |
| [ADR-003](ADR-003%20ENV%20UNICO%20NA%20RAIZ.md) | Um único `.env` na raiz | Aceita | Setup de ambiente |
| [ADR-004](ADR-004%20BACKEND%20EM%20FASTAPI.md) | Backend em FastAPI | Aceita | Camada de serviço |
| [ADR-005](ADR-005%20SEM%20AUTENTICACAO.md) | Sem autenticação | Aceita | **Segurança, deploy** |
| [ADR-006](ADR-006%20SQLALCHEMY%20COM%20SQL%20NAS%20ANALITICAS.md) | SQLAlchemy 2.0 + Alembic, com SQL nas analíticas | Aceita | Acesso a dados |
| [ADR-007](ADR-007%20FRONTEND%20REACT%20VITE%20TYPESCRIPT.md) | Frontend React + Vite + TypeScript | Aceita | Apresentação |
| [ADR-008](ADR-008%20LIMITACOES%20DOS%20DADOS%20EXPLICITAS%20NA%20UI.md) | Limitações dos dados explícitas na UI | Aceita | **Escopo do produto** |
| [ADR-009](ADR-009%20PACIENTES%20SEM%20NOME.md) | Pacientes sem nome, identificados por ID | Aceita | Listagens e busca |

## Leitura recomendada

Começando no projeto, leia nesta ordem:

1. **ADR-008** — define o que é possível construir. As limitações do dataset
   são o constrangimento mais forte do produto.
2. **ADR-001** e **ADR-002** — de onde vêm os dados e como estão no banco.
3. **ADR-004** e **ADR-006** — como o backend está organizado.
4. **ADR-005** — por que não há autenticação, e quando isso precisa mudar.

## ADRs com revisão obrigatória

Duas decisões têm data de validade implícita:

- **ADR-005 (sem autenticação)** — deve ser reaberta antes de qualquer exposição
  pública ou entrada de dado real
- **ADR-008 (limitações)** — se o dataset for regerado com valores de exame, boa
  parte das restrições de escopo cai

## Temas ainda sem ADR

| Tema | Situação |
|---|---|
| **Camada de agente de IA** | A definir. Uma ADR anterior propunha tool-calling sobre endpoints tipados; foi descartada para que a arquitetura de agentes seja decidida quando o tema for efetivamente abordado |
| Observabilidade e logging | A definir |
| Estratégia de deploy | A definir — ver ADR-005 antes |

## Formato

Cada ADR segue a mesma estrutura:

1. **Contexto** — o problema, com números medidos
2. **Decisão** — o que foi decidido e o que isso significa concretamente
3. **Alternativas descartadas** — o que foi considerado e por que não
4. **Consequências** — positivas, negativas com severidade e mitigação, e o
   impacto prático em quem implementa
5. **Gatilhos de revisão** — que evento obriga a reabrir a decisão
6. **Referências**

Os números citados foram **medidos no banco populado**, não estimados.
