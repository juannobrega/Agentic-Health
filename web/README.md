# FRONTEND

SPA React + Vite + TypeScript sobre a API (ADR-007).

## Desenvolvimento

```bash
cd web
npm install
npm run dev          # http://localhost:5173
```

O Vite faz proxy de `/api` para `http://localhost:8000`, então a origem é única
e não há CORS em desenvolvimento.

## Tipos gerados do OpenAPI

`src/api/tipos.ts` é **gerado** — não edite à mão:

```bash
npm run tipos             # regenera do OpenAPI (API precisa estar no ar)
npm run tipos:verificar   # falha se estiver defasado
```

`src/api/verificar-contrato.ts` cruza os tipos de domínio escritos à mão com o
contrato gerado. Se o backend renomear ou remover um campo, **o build falha** em
vez de a tela quebrar em runtime. Foi o que pegou três campos faltantes na
primeira integração.

## Telas

| Rota | Tela |
|---|---|
| `/` | Visão populacional: cards, pirâmide etária, distribuições |
| `/pacientes` | Lista com filtros (sexo, idade, condição) — filtros na URL |
| `/pacientes/:id` | Prontuário: timeline + abas por domínio + resumo |
| `/pacientes/:id/trajetoria` | Sequência de atendimentos encadeados |
| `/atendimentos` | Lista com filtro de tipo |
| `/atendimentos/:id` | Detalhe com todos os domínios |
| `/prevalencia` | Prevalência por domínio com corte demográfico |
| `/coortes` | Construtor com N ao vivo |

## Decisões de interface

**Exames exibem "não disponível", nunca vazio.** O dataset não traz resultados
(ADR-008); campo vazio pareceria defeito de software.

**Os filtros de qualidade são informados.** A aba de medicamentos mostra quantos
registros foram excluídos e por quê, em vez de filtrar em silêncio.

**Pacientes não têm nome.** O rótulo é `Paciente #<id>` e a busca é por
identificador — o OMOP é desidentificado por especificação (ADR-009).

**Filtros na URL.** `?sexo=F&idade_min=40` torna a view compartilhável e
sobrevive ao reload.

**Tema claro e escuro** por tokens CSS, respeitando `prefers-color-scheme`.

## Build

```bash
npm run build        # tsc -b && vite build
```
