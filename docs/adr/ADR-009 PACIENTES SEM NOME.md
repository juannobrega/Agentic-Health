# ADR-009 PACIENTES SEM NOME

| | |
|---|---|
| **Status** | Aceita |
| **Data** | 2026-10-02 |
| **Impacto** | Listagens, busca, cabeçalhos — toda referência a paciente |
| **Depende de** | ADR-001 |

---

## 1. Contexto

O OMOP CDM é **desidentificado por especificação**. A tabela `pessoa` não tem
campo de nome, sobrenome, documento, endereço ou telefone. Verificado no banco:

```
id_pessoa | codigo_origem_pessoa                 | sexo | raca   | ano_nascimento
        1 | 0033e4bc-e630-47be-8c89-fcd332cef687 | M    | branca | 1974
        2 | 0062fa0d-3ae2-4f99-93b0-e404e062e4f5 | F    | branca | 1950
```

Cada paciente é identificado por:
- **`id_pessoa`** — inteiro sequencial, 1 a 1.130
- **`codigo_origem_pessoa`** — UUID gerado pelo Synthea

Isso tem consequência direta no produto: **não existe "buscar paciente por
nome"**, e cada registro precisa de um rótulo legível em listas, cabeçalhos,
breadcrumbs e resultados de coorte.

A alternativa seria gerar nomes fictícios para a interface parecer natural — o
que é comum em demos de sistemas de saúde.

## 2. Decisão

**Manter os pacientes sem nome.** O rótulo de exibição é `Paciente #<id>`,
complementado por sexo e idade quando houver espaço:

```
Paciente #1 · M, 51 anos
Paciente #736 · M, 32 anos
```

A busca opera sobre **ID, UUID e filtros clínicos/demográficos** — nunca sobre nome.

### 2.1 Nomes fictícios foram considerados e recusados

Esta é a parte substantiva da decisão. Gerar "Maria Silva" para o paciente #1
tornaria a UI mais apresentável, e foi avaliado seriamente.

**Recusado por três razões:**

1. **Em um sistema de saúde, um nome na tela é lido como identidade real.** O
   contexto visual de um prontuário — diagnósticos, medicamentos, alergias —
   carrega a expectativa de que aquilo descreve uma pessoa. Um nome inventado
   nesse contexto convida à confusão entre dado simulado e dado de paciente.

2. **O risco sobrevive ao rótulo.** Mesmo marcando "dados sintéticos" na tela,
   um screenshot, uma exportação em CSV ou uma tela compartilhada perde o
   contexto. O nome viaja; o aviso não.

3. **O ganho é puramente estético.** Nenhuma funcionalidade depende de nome.
   Busca, filtro, coorte e navegação funcionam por ID. Trocar risco clínico por
   aparência de demo não se paga.

### 2.2 Se um nome vier a ser necessário

Caso um rótulo mais amigável se torne requisito, a implementação deve ser:

- **Determinística** a partir do `id_pessoa` — o mesmo paciente sempre com o
  mesmo rótulo, sem estado adicional
- **Obviamente sintético** — ex. nomes de um conjunto fictício reconhecível,
  nunca nomes brasileiros comuns que pareçam reais
- **Rotulado na própria UI** como gerado, adjacente ao nome e não em rodapé

## 3. Alternativas descartadas

| Alternativa | Por que não |
|---|---|
| **Nomes fictícios realistas** (Faker pt-BR) | Indistinguíveis de dado real; risco clínico sem ganho funcional |
| **Nomes óbvios** ("Paciente Alfa", "Paciente Beta") | Melhor que o anterior, mas adiciona um mapeamento a manter sem resolver nada que o ID já resolva |
| **Iniciais fictícias** ("J.P.S.") | Mimetiza exatamente a convenção de desidentificação de dado **real**, o que é mais confuso, não menos |
| **Só o UUID** | Ilegível e impossível de comunicar verbalmente ("o paciente 0033e4bc...") |
| **Hash curto** do UUID | Compacto, mas sem vantagem sobre o `id_pessoa`, que já é curto e sequencial |

## 4. Consequências

### 4.1 Positivas

- **Nenhuma ambiguidade** sobre o que é dado real: não há identidade falsa na tela
- Alinhado ao propósito do OMOP — modelo desidentificado permanece desidentificado
- Busca por ID e UUID é **exata**, sem fuzzy matching nem normalização de acento
- Reduz o risco de alguém tratar o dataset sintético como base real (ADR-005)
- Um campo a menos para manter, traduzir e indexar

### 4.2 Negativas e riscos

| Risco | Severidade | Mitigação |
|---|---|---|
| Listas de pacientes **visualmente áridas** — colunas de números | Média | Enriquecer o rótulo com sexo, idade e condição principal; dar peso visual ao que é clínico, não ao ID |
| Difícil **lembrar ou conversar** sobre um paciente específico | Média | ID curto e sequencial (1-1.130) é mais memorável que UUID. Filtros na URL tornam a view compartilhável (ADR-007) |
| Demos exigem **explicar** por que não há nomes | Baixa | Uma frase: "OMOP é desidentificado por especificação" |
| Alguém adicionar nome fictício depois **sem ler esta ADR** | Média | Esta ADR existe para registrar que a opção foi avaliada e recusada, com o motivo |
| Usuário tentar buscar por nome e não encontrar o campo | Baixa | Placeholder do campo de busca explícito: "ID ou UUID do paciente" |

### 4.3 Impacto em quem implementa

**Nunca invente nome de paciente.** Nem em mock, nem em teste, nem em seed de
demo. O rótulo é `Paciente #<id>`.

**O campo de busca não aceita nome.** Deixe isso explícito no placeholder:
```tsx
// ERRADO — promete o que não existe
<input placeholder="Buscar paciente..." />

// CORRETO
<input placeholder="Buscar por ID ou UUID" />
```

**Componha o rótulo com dado clínico, não só o ID.** `Paciente #1 · M, 51 anos`
é mais útil que `Paciente #1` e não custa nada:
```tsx
function rotuloPaciente(p: Paciente): string {
  return `Paciente #${p.id_pessoa} · ${p.sexo}, ${p.idade} anos`;
}
```

**Em exportação CSV, inclua o UUID.** É o identificador estável para cruzar com
outra fonte; o `id_pessoa` é sequencial e específico desta carga.

## 5. Gatilhos de revisão

- Projeto passar a usar **dados reais** → nomes reais entram, com toda a
  proteção que isso exige (ADR-005)
- Requisito explícito de **demo comercial** com aparência de produto final →
  implementar conforme a seção 2.2, nunca com nomes realistas
- Integração com sistema externo que **forneça identificação** → avaliar como
  exibir sem comprometer a desidentificação da base

## 6. Referências

- ADR-001 (dataset OMOP), ADR-005 (sem autenticação), ADR-007 (frontend)
- [OMOP CDM — tabela PERSON](https://ohdsi.github.io/CommonDataModel/cdm54.html#person)
