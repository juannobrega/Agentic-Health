# ADR-007 FRONTEND REACT VITE TYPESCRIPT

| | |
|---|---|
| **Status** | Aceita |
| **Data** | 2026-10-02 |
| **Impacto** | Toda a camada de apresentação |
| **Depende de** | ADR-004, ADR-005 |

---

## 1. Contexto

O frontend precisa de telas densas em dados:

- **Prontuário** com timeline de até 2.486 eventos num único paciente
- **Listas paginadas** com filtros combinados sobre 1.130 pacientes e 32.153 atendimentos
- **Construtor de coortes** com feedback do N a cada mudança de critério
- **Gráficos** de prevalência e distribuição demográfica

Requisitos que moldam a escolha:

1. **Sem SEO.** É ferramenta interna de exploração clínica, atrás de uma API sem
   autenticação que não pode ser exposta publicamente (ADR-005). Nenhuma página
   precisa ser indexada.
2. **Contrato tipado com o backend.** A API tem campos nulos por limitação
   estrutural (ADR-008); a UI precisa tratá-los explicitamente, e uma mudança de
   contrato deve falhar no build, não na tela.
3. **Iteração visual frequente.** Telas de prontuário e dashboard exigem muitos
   ciclos de ajuste.

## 2. Decisão

**React 18 + Vite + TypeScript**, SPA. TanStack Query para dados do servidor,
React Router para navegação. Tipos gerados do OpenAPI da API.

### 2.1 Estrutura proposta

```
web/
├── Dockerfile
├── package.json
├── vite.config.ts
├── src/
│   ├── main.tsx
│   ├── api/
│   │   ├── tipos.ts          GERADO do OpenAPI — não editar à mão
│   │   └── cliente.ts        wrapper de fetch
│   ├── paginas/
│   │   ├── Dashboard.tsx
│   │   ├── ListaPacientes.tsx
│   │   ├── Prontuario.tsx
│   │   ├── Atendimento.tsx
│   │   ├── Trajetoria.tsx
│   │   ├── Coortes.tsx
│   │   └── Condicoes.tsx
│   ├── componentes/
│   │   ├── Timeline.tsx
│   │   ├── TabelaPaginada.tsx
│   │   ├── FiltrosDemograficos.tsx
│   │   └── AvisoLimitacaoDado.tsx
│   └── hooks/
```

### 2.2 Tipos gerados, não escritos

O OpenAPI da API (ADR-004) gera `src/api/tipos.ts`:

```bash
npx openapi-typescript http://localhost:8000/openapi.json -o src/api/tipos.ts
```

Isso significa que renomear um campo no backend **quebra o build do frontend** —
exatamente o comportamento desejado. O alternativo (tipos escritos à mão)
divergiria silenciosamente e produziria `undefined` em produção.

**O arquivo gerado não é editado à mão.** Um script `npm run tipos` o regenera.

### 2.3 Por que TanStack Query

As telas têm padrões que seriam reimplementados em cada página sem ele:

| Necessidade | O que o TanStack Query resolve |
|---|---|
| Timeline paginada com scroll | `useInfiniteQuery` com cursor |
| Prévia de coorte a cada mudança de filtro | Debounce + cancelamento de request obsoleto |
| Navegar entre pacientes e voltar | Cache por chave, sem refetch desnecessário |
| Estados de carregando/erro/vazio | `isLoading`, `isError` padronizados |

### 2.4 Tratamento dos nulos estruturais

O componente `AvisoLimitacaoDado` é o lugar único onde as limitações do dataset
aparecem na UI (ADR-008). A coluna de valor de exame renderiza "não disponível",
não vazio — a diferença entre "o sistema não tem" e "o sistema quebrou".

## 3. Alternativas descartadas

| Alternativa | Por que não |
|---|---|
| **Next.js** | SSR e rotas de servidor são o ponto forte, e não precisamos de nenhum: sem SEO, sem página pública. Adicionaria um servidor Node ao compose sem benefício |
| **Vue + Nuxt** | Tecnicamente adequado. Recusado por familiaridade de ecossistema e volume de bibliotecas de tabela/gráfico em React |
| **Svelte/SvelteKit** | Bundle menor e DX agradável, mas ecossistema menor para tabelas densas e componentes clínicos |
| **Angular** | Estrutura e DI robustas, porém peso desproporcional para 8 telas |
| **Streamlit / Dash** | Muito rápido para dashboards analíticos, e tentador para o item de estatísticas. Recusado porque prontuário e construtor de coortes exigem interação e layout que essas ferramentas não entregam bem |
| **HTMX + templates no FastAPI** | Elimina o frontend como serviço separado e seria defensável. Recusado pela timeline e pelo construtor de coortes, que têm estado de cliente complexo |
| **JavaScript sem TypeScript** | Perderia a validação de contrato, que é um dos três requisitos |

## 4. Consequências

### 4.1 Positivas

- **HMR do Vite** mantém o ciclo de iteração visual rápido
- **Tipos derivados do OpenAPI**: mudança de contrato falha no build
- TanStack Query evita reimplementar cache, revalidação e estados em cada tela
- SPA é suficiente e simples: sem servidor de renderização
- Ecossistema amplo para tabelas, gráficos e componentes de data-heavy UI

### 4.2 Negativas e riscos

| Risco | Severidade | Mitigação |
|---|---|---|
| **Tipos gerados ficam obsoletos** se ninguém regenerar | **Alta** | `npm run tipos` no fluxo; idealmente verificação no CI que falha se o arquivo gerado divergir do OpenAPI atual |
| Timeline com **2.486 eventos** travar o render | **Alta** | Virtualização de lista obrigatória; paginação no servidor; nunca renderizar a lista completa |
| Sem SSR, primeira carga depende de **JS** | Baixa | Irrelevante para ferramenta interna |
| **node_modules e build** adicionam peso ao compose | Baixa | Multi-stage Dockerfile; em dev, Vite serve direto |
| **Estado de filtro** espalhado entre páginas | Média | Filtros na URL (query string) — torna a view compartilhável e sobrevive a reload |
| CORS mal configurado entre API e frontend | Média | Origem explícita no backend; variável no `.env` da raiz (ADR-003) |
| Gráficos ilegíveis em tema escuro | Baixa | Paleta com tokens de tema; testar nos dois modos |

### 4.3 Impacto em quem implementa

**Nunca edite `src/api/tipos.ts` à mão.** É gerado. Se o tipo está errado, o
contrato da API está errado — corrija o backend e regenere.

**Toda lista longa precisa de virtualização.** A timeline do paciente 736 tem
2.486 exames. Renderizar tudo congela a aba:
```tsx
// ERRADO
{eventos.map(e => <EventoTimeline key={e.pk} {...e} />)}

// CORRETO: virtualizado + paginado no servidor
<VirtualList items={eventos} renderItem={...} />
```

**Filtros vão na URL.** `?sexo=F&idade_min=40` em vez de estado local — a tela
fica compartilhável e sobrevive ao reload.

**Trate os nulos estruturais explicitamente.** `valor_numerico` é sempre nulo
neste dataset; renderizar string vazia faz parecer bug:
```tsx
// ERRADO
<td>{exame.valor_numerico}</td>

// CORRETO
<td>{exame.valor_numerico ?? <span className="indisponivel">não disponível</span>}</td>
```

**Nunca invente nome de paciente** (ADR-009). O rótulo é `Paciente #<id>`.

## 5. Gatilhos de revisão

- Necessidade de **página pública ou indexável** → Next.js volta à mesa
- Volume de dado por tela crescer muito além de virtualização → repensar paginação
- Surgir **app mobile** → avaliar React Native ou PWA
- Equipe mudar de stack predominante → reavaliar framework

## 6. Referências

- ADR-004 (backend e OpenAPI), ADR-005 (sem auth), ADR-006 (ORM),
  ADR-008 (limitações na UI), ADR-009 (pacientes sem nome)
- [Vite](https://vitejs.dev) · [TanStack Query](https://tanstack.com/query) ·
  [openapi-typescript](https://github.com/drwpow/openapi-typescript)
