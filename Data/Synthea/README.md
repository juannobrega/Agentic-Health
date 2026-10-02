# Synthea — dataset OMOP CDM em português

Dataset sintético Synthea (OMOP CDM v5.x) traduzido para português: **nomes de
arquivos, nomes de colunas, valores demográficos e nomes clínicos** derivados dos
códigos SNOMED CT, LOINC e RxNorm.

> Os CSVs originais em inglês foram removidos — esta pasta contém apenas a versão
> traduzida. Para recuperar o schema OMOP em inglês, é preciso regerar a partir do
> [Synthea](https://github.com/synthetichealth/synthea).

**311.741 linhas** · **1.130 pacientes** · cobertura **1909 → jan/2019**

## Arquivos

| Arquivo | Linhas | Descrição |
|---|---|---|
| `pessoa.csv` | 1.130 | Demografia dos pacientes |
| `periodo_observacao.csv` | 1.126 | Janela de observação por paciente |
| `atendimento.csv` | 32.153 | Atendimentos/visitas |
| `condicao.csv` | 7.900 | Diagnósticos |
| `exposicao_medicamento.csv` | 29.518 | Medicamentos prescritos |
| `procedimento.csv` | 17.333 | Procedimentos realizados |
| `exame.csv` | 199.514 | Exames e sinais vitais |
| `observacao.csv` | 8.518 | Observações clínicas (alergias etc.) |
| `periodo_condicao.csv` | 7.897 | Períodos agregados de condição |
| `periodo_medicamento.csv` | 6.652 | Períodos agregados de medicação |
| `dicionario_conceitos.csv` | 535 | De-para código → nome em português |

## O que foi traduzido

**Nomes de colunas** — `person_id` → `id_pessoa`, `year_of_birth` → `ano_nascimento`,
`value_as_number` → `valor_numerico`, etc.

**Valores demográficos** em `pessoa.csv`:
- `raca`: branca, preta, amarela, hispânica, indígena, outra, Desconhecida
- `etnia`: irlandesa, italiana, inglesa, francesa, porto-riquenha, alemã… (25 valores)

**Colunas novas** (não existiam no original, acrescentadas pela tradução):
- `nome_condicao`, `nome_procedimento`, `nome_medicamento`, `nome_exame`, `nome_observacao`
  — o nome clínico em português, resolvido a partir do código-fonte
- `sexo_descricao`, `raca_descricao` (em `pessoa.csv`), `atendimento_descricao` (em `atendimento.csv`)
  — decodificação dos `concept_id` do OMOP
- `inconsistencia_vocabulario` (em `exposicao_medicamento.csv`) — ver ressalvas abaixo

Todas as colunas originais foram **preservadas intactas**, incluindo os `concept_id`.
A tradução é aditiva: nada do dado original foi sobrescrito, exceto `raca` e `etnia`.

## ⚠️ Ressalvas importantes sobre os dados

Estas são limitações do **dataset original**, não da tradução.

### 1. `exame.csv` não tem resultados

A maior tabela (199.514 linhas) tem **zero valores numéricos**. As colunas
`valor_numerico`, `id_conceito_valor`, `unidade`, `limite_inferior`, `limite_superior`
e `valor_origem` estão **todas vazias**. Só sobrou *qual* exame foi pedido e *quando*.

Isso inviabiliza qualquer análise baseada em valor: tendência de laboratório, controle
pressórico, IMC, fenotipagem por limiar. A tabela serve apenas como sinal de
"exame foi realizado". Para ter valores, é preciso regerar a partir do Synthea.

### 2. Códigos de condição usados como medicamento (bug de ETL)

**7.899 das 29.518 linhas** (26,8%) de `exposicao_medicamento.csv` têm
`codigo_origem_medicamento` preenchido com um código **SNOMED de condição**
(ex.: `444814009` = infecção viral das vias aéreas superiores) em vez de um
código RxNorm de fármaco. São exatamente as linhas com `id_conceito_medicamento = 0`.

Essas linhas estão marcadas na coluna **`inconsistencia_vocabulario`** com o valor
`codigo_de_condicao`. **Filtre-as** ao analisar medicamentos:

```python
import pandas as pd
med = pd.read_csv('exposicao_medicamento.csv')
med_real = med[med['inconsistencia_vocabulario'].isna()]   # 21.619 linhas válidas
```

O `nome_medicamento` dessas linhas traz o nome da condição, não de um fármaco —
é o que o código de fato representa, e por isso a coluna de inconsistência existe.

### 3. IDs primários duplicados em 3 tabelas

O Synthea repete identificadores que deveriam ser únicos, apontando para registros
clinicamente **distintos** (pacientes, datas e códigos diferentes):

| Tabela | Linhas | IDs distintos | Repetidos |
|---|---|---|---|
| `exame.csv` | 199.514 | 170.043 | 29.471 |
| `exposicao_medicamento.csv` | 29.518 | 13.799 | 7.899 |
| `observacao.csv` | 8.518 | 7.899 | 619 |

Exemplo — `id_exposicao_medicamento = 1` aparece 3 vezes, com medicamentos e datas
diferentes. Nenhum par de linhas duplicadas é idêntico: são registros reais.

Consequência prática: **não use essas colunas como chave** em join, deduplicação ou
índice único. A carga em `Data/DB` resolve isso com uma chave substituta.

### 4. Prescrições clinicamente implausíveis

O Synthea atribui medicamentos sem validar plausibilidade contra a idade.
**117 pacientes menores de 18 anos** têm prescrição de fármaco tipicamente
adulto (metformina, tansulosina, atorvastatina, varfarina).

Exemplo: o paciente `7`, nascido em 2013, tem **metformina registrada aos 2
anos**, junto com tansulosina e atorvastatina.

Não use este dataset para validar regras de prescrição, alertas de
contraindicação por idade ou lógica de segurança medicamentosa.

### 5. Outros pontos de atenção

- **2 anos de nascimento impossíveis**: `id_pessoa` 265 (2099) e 332 (1099). Filtre.
- **44 pacientes com 110-119 anos** — cauda longa conhecida do Synthea.
- **`observacao.csv`: 83% com `id_conceito_observacao = 0`** (não mapeado no OMOP).
  O `nome_observacao` foi resolvido pelo código-fonte, então é utilizável, mas não
  por concept_id padrão.
- **Sem dimensão geográfica ou de prestador**: `id_local`, `id_profissional` e
  `id_unidade_saude` estão 100% vazios.
- **Raça enviesada** (75% branca) — não serve como coorte de avaliação de equidade.

## Como os nomes clínicos foram traduzidos

Os 535 códigos distintos foram traduzidos **sem o vocabulário oficial do OHDSI**
(`CONCEPT.csv` do Athena não está disponível neste repositório):

| Vocabulário | Códigos |
|---|---|
| SNOMED CT | 272 |
| RxNorm | 146 |
| LOINC | 117 |

Isso significa que os nomes são **tradução direta dos códigos, sem fonte auditável**.
Para uso clínico ou regulatório, valide contra o Athena (athena.ohdsi.org) baixando
`CONCEPT.csv` e fazendo join por `concept_code`.

## Compatibilidade com ferramentas OHDSI

Os nomes de tabelas e colunas em português **quebram a compatibilidade** com Atlas,
Achilles e demais ferramentas do stack OHDSI, que exigem o schema OMOP em inglês.
Esta pasta serve para análise exploratória e interface em português. Para usar as
ferramentas OHDSI seria necessário regerar o dataset em inglês a partir do Synthea,
ou remapear as colunas de volta ao schema OMOP.

## Dicionário de conceitos

`dicionario_conceitos.csv` traz o de-para completo dos 535 códigos usados no dataset:

| coluna | conteúdo |
|---|---|
| `codigo_origem` | código SNOMED CT / LOINC / RxNorm |
| `vocabulario` | qual dos três |
| `nome_portugues` | tradução |
| `dominios` | em que tabelas o código aparece |
| `ocorrencias` | quantas linhas usam |
| `observacao` | marca os 134 códigos afetados pelo bug de ETL |

É a referência para conferir ou corrigir qualquer nome clínico nos CSVs.
