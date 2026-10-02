# ADR-001 DATASET OMOP SINTETICO COMO FONTE UNICA

| | |
|---|---|
| **Status** | Aceita |
| **Data** | 2026-10-02 |
| **Decisores** | Equipe Agentic Health |
| **Impacto** | Todo o produto — define o que é possível construir |

---

## 1. Contexto

O projeto precisa de dados clínicos longitudinais para desenvolver e validar
prontuário e coortes. Três caminhos existiam:

1. **Dados reais de pacientes** — exigiria aprovação de comitê de ética,
   contrato de uso de dados, desidentificação auditada, ambiente com
   conformidade LGPD e trilha de auditoria de acesso. Meses de trabalho antes
   da primeira linha de código de produto.
2. **Dados fabricados à mão** — rápido, mas sem correlação clínica real: um
   paciente com hipertensão não teria o padrão de atendimentos, medicamentos e
   comorbidades que a doença produz. Validaria a tela, não o produto.
3. **Dados sintéticos gerados por simulador** — o [Synthea](https://github.com/synthetichealth/synthea)
   simula histórias de vida completas a partir de módulos de doença baseados em
   literatura e dados epidemiológicos reais do Massachusetts.

O Synthea exporta no padrão **OMOP CDM v5.x** (Observational Medical Outcomes
Partnership), o modelo de dados do consórcio OHDSI usado por centenas de
instituições para pesquisa observacional.

## 2. Decisão

Adotar o **dataset Synthea traduzido para português** como fonte única de dados,
em `Data/Synthea`.

### 2.1 O que isso concretamente significa

O dataset tem **10 tabelas, 311.741 linhas, 1.130 pacientes**, cobrindo
**1909 a janeiro de 2019**:

| Tabela | Linhas | Papel |
|---|---|---|
| `exame` | 199.514 | Exames e sinais vitais pedidos |
| `atendimento` | 32.153 | Visitas (ambulatorial, emergência, internação) |
| `exposicao_medicamento` | 29.518 | Prescrições |
| `procedimento` | 17.333 | Procedimentos realizados |
| `observacao` | 8.518 | Observações, incluindo 619 alergias |
| `condicao` | 7.900 | Diagnósticos |
| `periodo_condicao` | 7.897 | Períodos agregados de condição |
| `periodo_medicamento` | 6.652 | Períodos agregados de medicação |
| `pessoa` | 1.130 | Demografia |
| `periodo_observacao` | 1.126 | Janela de observação por paciente |

### 2.2 A tradução

Os CSVs originais em inglês foram **removidos**. A versão em português traduziu
quatro camadas:

- **Nomes de arquivo**: `drug_exposure.csv` → `exposicao_medicamento.csv`
- **Nomes de coluna**: `person_id` → `id_pessoa`, `value_as_number` → `valor_numerico`
- **Valores demográficos**: `white` → `branca`, `irish` → `irlandesa` (34 strings)
- **Nomes clínicos**: os **535 códigos** SNOMED CT (272), RxNorm (146) e
  LOINC (117) viraram colunas novas `nome_condicao`, `nome_medicamento`,
  `nome_exame`, `nome_procedimento`, `nome_observacao`

A tradução é **aditiva**: as colunas originais foram preservadas intactas,
incluindo todos os `concept_id` do OMOP. Validação célula a célula confirmou
**zero divergência** em 311.741 linhas. Apenas `raca` e `etnia` foram
substituídas no lugar.

O de-para completo vive em `Data/Synthea/dicionario_conceitos.csv`.

## 3. Alternativas descartadas

| Alternativa | Por que não |
|---|---|
| Dados reais | Bloqueio ético/legal de meses; risco de exposição de dado pessoal |
| Dados fabricados à mão | Sem correlação clínica: validaria UI, não o produto |
| Synthea em inglês | Interface e documentação do projeto são em português; traduzir na camada de apresentação espalharia o dicionário pelo código |
| Synthea + vocabulário OHDSI (Athena) | O `CONCEPT.csv` do Athena tem ~500MB e exige registro. Para 535 códigos, o custo não se paga nesta fase |

## 4. Consequências

### 4.1 Positivas

- **Nenhuma restrição de privacidade.** Dados sintéticos podem ser versionados,
  compartilhados e usados em demo sem consentimento ou anonimização.
- **Correlação clínica preservada.** Um paciente diabético tem o padrão de
  atendimentos, medicamentos e comorbidades que a doença produz.
- **Padrão reconhecível.** Quem trabalha com dados de saúde reconhece o OMOP;
  a modelagem não precisa ser explicada do zero.
- **Nomes em português já resolvidos**, sem dependência de serviço externo em runtime.

### 4.2 Negativas e riscos

| Risco | Severidade | Mitigação |
|---|---|---|
| Traduções dos 535 códigos **sem fonte auditável** | **Alta** para uso clínico | `dicionario_conceitos.csv` isola o de-para num arquivo; validar contra o Athena antes de qualquer uso real. Documentado no README do dataset. |
| Schema em português **quebra ferramentas OHDSI** (Atlas, Achilles) | Média | Aceito: o projeto não usa o stack OHDSI. Reverter exigiria regerar em inglês. Ver ADR-002. |
| Originais em inglês **foram apagados** | Média | Recuperável apenas regerando do Synthea. O dicionário e os códigos-fonte preservados permitem reconstruir o mapeamento. |
| Dataset tem **limitações severas** que moldam o produto | **Alta** | Tratadas como requisito de primeira classe. Ver ADR-008. |
| População **não representativa** (75% branca, Massachusetts) | Média | Inadequado para qualquer análise de equidade. Documentado. |

### 4.3 Impacto em quem implementa

- **Sempre use as colunas `nome_*`** para exibição, nunca os `concept_id` crus.
- **Não confie em `concept_id` para filtrar**: `observacao` tem 83% de conceitos
  não mapeados (valor `0`). Filtre pelo `codigo_origem_*` ou pelo `nome_*`.
- Ao adicionar uma consulta que exiba um código ainda não traduzido, acrescente
  a entrada em `dicionario_conceitos.csv` — não traduza inline no código.
- O dataset é **somente leitura**. Nenhum código de produto escreve nele.

## 5. Gatilhos de revisão

Esta ADR deve ser reaberta se:

- O projeto passar a usar **dados reais de pacientes** — muda tudo: ética,
  autenticação (ADR-005), auditoria, infraestrutura
- For necessário usar **ferramentas OHDSI** sobre esta base
- As traduções precisarem de **validação formal** para uso clínico ou regulatório
- O dataset for **regerado** com valores de exame (ver ADR-008)

## 6. Referências

- `Data/Synthea/README.md` — documentação do dataset e suas ressalvas
- `Data/Synthea/dicionario_conceitos.csv` — de-para dos 535 códigos
- [Synthea](https://github.com/synthetichealth/synthea) · [OMOP CDM](https://ohdsi.github.io/CommonDataModel/) · [Athena](https://athena.ohdsi.org)
- ADR-002 (banco), ADR-006 (ORM), ADR-008 (limitações na UI), ADR-009 (pacientes sem nome)
