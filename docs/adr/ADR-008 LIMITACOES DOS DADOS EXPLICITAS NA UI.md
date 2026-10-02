# ADR-008 LIMITACOES DOS DADOS EXPLICITAS NA UI

| | |
|---|---|
| **Status** | Aceita |
| **Data** | 2026-10-02 |
| **Impacto** | Produto inteiro — define o que pode ser construído |
| **Depende de** | ADR-001, ADR-002 |

---

## 1. Contexto

O dataset tem quatro limitações severas, descobertas durante a análise e a carga.
Elas não são detalhes técnicos: **determinam quais telas são possíveis**.

### 1.1 `exame` não tem resultados — a limitação mais grave

A maior tabela do banco (**199.514 linhas, 44MB**) tem **zero valores**.
Verificado coluna por coluna:

| Coluna | Preenchidas |
|---|---|
| `valor_numerico` | **0 de 199.514** |
| `id_conceito_valor` | todas `0` |
| `unidade` / `id_conceito_unidade` | todas vazias |
| `limite_inferior` / `limite_superior` | todas vazias |
| `valor_origem` | todas vazias |

Sobrou apenas *qual* exame foi pedido e *quando*. Os códigos LOINC são os
esperados (`8480-6` pressão sistólica, `4548-4` HbA1c, `29463-7` peso), mas
**toda leitura está em branco** — os resultados se perderam no ETL do Synthea.

**Consequência direta:** nenhuma análise baseada em valor é possível. Sem
tendência de laboratório, sem controle pressórico, sem curva de HbA1c, sem
cálculo de IMC, sem alerta de valor crítico, sem fenotipagem por limiar.

### 1.2 Códigos de condição usados como medicamento

**7.899 das 29.518 linhas (26,8%)** de `exposicao_medicamento` têm
`codigo_origem_medicamento` preenchido com **SNOMED de condição** em vez de
RxNorm de fármaco. São exatamente as linhas com `id_conceito_medicamento = 0`.

Exemplo real — `id_exposicao_medicamento = 1` traz três linhas, e a primeira é
um diagnóstico:

```
43878008  → Faringite estreptocócica   ← diagnóstico, não medicamento
834102    → Naproxeno 500mg            ← medicamento real
140       → Acetaminofeno              ← medicamento real
```

Sem filtro, um ranking de "top medicamentos" lista **"Infecção viral das vias
aéreas superiores"** em primeiro lugar — o que parece bug de software, não de dado.

### 1.3 IDs primários duplicados

| Tabela | Linhas | IDs distintos | Repetidos |
|---|---|---|---|
| `exame` | 199.514 | 170.043 | 29.471 |
| `exposicao_medicamento` | 29.518 | 13.799 | 7.899 |
| `observacao` | 8.518 | 7.899 | 619 |

Tratado no banco com chave substituta (ADR-002), mas afeta a API: o ID exposto
ao cliente precisa ser o `pk`, não o ID original.

### 1.4 Outras

- **2 anos de nascimento impossíveis**: `id_pessoa` 265 (2099) e 332 (1099)
- **44 pacientes com 110-119 anos** — cauda longa do Synthea
- **`observacao` com 83% de `concept_id = 0`** — não mapeado no OMOP
- **Sem dimensão geográfica ou de prestador**: `id_local`, `id_profissional`,
  `id_unidade_saude` 100% vazios
- **Raça 75% branca** — inadequado para análise de equidade

### 1.5 O problema de produto

Uma tela de exames sem valores **parece defeito de software**. Um gráfico de
medicamentos listando diagnósticos **parece bug**. Em ambos os casos o usuário
desconfia do sistema, não do dado — e perde confiança no produto inteiro.

## 2. Decisão

Tratar as limitações como **informação de primeira classe**, visível na
interface e declarada na API. Não esconder, não silenciar, não contornar.

### 2.1 Três camadas de tratamento

| Camada | Mecanismo |
|---|---|
| **Banco** | Views que encapsulam os filtros (`vw_medicamento_valido`, `vw_pessoa_valida`) e coluna `inconsistencia_vocabulario` marcando as linhas afetadas |
| **API** | `description` nos esquemas Pydantic explicando o nulo estrutural; resposta declara os filtros aplicados e quantos registros foram excluídos |
| **UI** | Componente `AvisoLimitacaoDado`; valor indisponível renderizado como "não disponível", nunca vazio |

### 2.2 Regras concretas

**Exames:** a tela exibe aviso de que o dataset não traz resultados. A coluna de
valor mostra "não disponível". **Nenhuma tela promete** gráfico de tendência,
controle pressórico ou IMC.

**Medicamentos:** toda consulta usa `vw_medicamento_valido` por padrão. A
resposta informa quantos registros foram excluídos e por quê; a UI mostra isso
como nota de rodapé, não como erro.

**Pacientes:** listagens excluem os 2 registros implausíveis por padrão
(`1.128 de 1.130`), com parâmetro para incluí-los.

**IDs:** a API expõe `pk` como identificador nas três tabelas afetadas.

### 2.3 O que NÃO construir

Esta ADR também é uma lista de exclusão. Não entram no backlog:

- Gráfico de tendência de qualquer exame
- Dashboard de sinais vitais
- Cálculo de IMC, controle pressórico ou classificação de HbA1c
- Alerta de valor laboratorial crítico
- Mapa de pacientes ou filtro por unidade/médico
- Análise de equidade racial

## 3. Alternativas descartadas

| Alternativa | Por que não |
|---|---|
| **Esconder a tabela de exames** | Perderia informação real e útil: qual exame foi pedido e quando. A frequência de pedido é um sinal clínico válido |
| **Gerar valores sintéticos para os exames** | **Recusada com firmeza.** Inventar resultado de laboratório num sistema de saúde é criar dado clínico falso indistinguível de real. Mesmo rotulado, viraria base de conclusão errada |
| **Filtrar medicamentos silenciosamente** | Funcionaria, mas esconderia que 26,8% dos dados têm problema — e alguém eventualmente investigaria a divergência de contagem sem pista |
| **Descartar as linhas com ID duplicado** | Perderia 38 mil registros clínicos reais |
| **Corrigir o mapeamento dos 7.899 códigos** | Não há informação para isso: o código de condição não diz qual medicamento deveria estar ali. A informação se perdeu |
| **Regerar o dataset do Synthea** | **A solução de verdade** para a limitação 1.1, e deve ser considerada. Não bloqueia o desenvolvimento atual, mas destravaria a maior parte do valor clínico |

## 4. Consequências

### 4.1 Positivas

- Usuário distingue **"o sistema não tem esse dado"** de **"o sistema quebrou"**
- Impede construir telas que o dado não sustenta — economiza trabalho jogado fora
- Filtros de qualidade ficam **auditáveis** nas views, não escondidos em queries
- A lista de exclusão dá clareza de escopo ao backlog

### 4.2 Negativas e riscos

| Risco | Severidade | Mitigação |
|---|---|---|
| Avisos espalhados **poluem a UI** e soam defensivos | Média | Componente único e discreto; aviso por contexto, não repetido em cada linha |
| Dataset regerado deixa **avisos obsoletos** contradizendo o dado | **Alta** | Avisos derivados da API (que sabe se há valores), não hardcoded na UI. Se `valor_numerico` passar a vir preenchido, o aviso desaparece sozinho |
| UI **acoplada** a detalhes do dataset | Média | Concentrar no componente de aviso e na camada de API; páginas não conhecem os números |
| Expectativa frustrada: usuário quer gráfico de exame | Média | Deixar explícito desde a primeira tela, não ao final do fluxo |
| Contagem de excluídos vira **número mágico** | Baixa | Calculado pela API em runtime, não constante no código |

### 4.3 Impacto em quem implementa

**Backend:** toda consulta de medicamento usa o modelo `MedicamentoValido`
(a view), nunca `ExposicaoMedicamento`. Toda resposta que aplique filtro de
qualidade declara isso na própria resposta:
```python
class ListaMedicamentos(BaseModel):
    itens: list[Medicamento]
    total: int
    excluidos_por_qualidade: int
    motivo_exclusao: str = "Código SNOMED de condição em vez de RxNorm (ADR-008)"
```

**Backend:** campos nulos estruturais levam `description` no esquema Pydantic —
é o que chega ao frontend via OpenAPI.

**Frontend:** nunca renderize nulo estrutural como vazio. "não disponível" é a
diferença entre dado ausente e bug.

**Frontend:** o aviso vem da API, não de constante no código. Hardcoded, ele
sobrevive ao problema e passa a mentir.

**Todos:** antes de propor uma tela ou endpoint, verifique na seção 2.3 se o dado
sustenta. Um gráfico de tendência de glicemia é impossível, não difícil.

## 5. Gatilhos de revisão

| Gatilho | O que muda |
|---|---|
| **Dataset regerado com valores de exame** | Remove a limitação 1.1 — destrava gráficos, tendências, IMC e fenotipagem. Avisos devem desaparecer |
| Mapeamento dos medicamentos corrigido na origem | Remove a limitação 1.2 e a view de filtro |
| IDs corrigidos na origem | Permite remover a chave substituta (ADR-002) |
| Entrada de dado real | Todas as limitações mudam; reavaliar do zero |

**Recomendação:** regerar o dataset a partir do Synthea com os valores de exame
intactos é a ação de maior impacto disponível para o produto hoje.

## 6. Referências

- `Data/Synthea/README.md` — as quatro limitações documentadas em detalhe
- `Data/DB/sql/03_views.sql` — as views de qualidade
- ADR-001 (dataset), ADR-002 (chave substituta), ADR-006 (ORM e views), ADR-009 (sem nomes)
