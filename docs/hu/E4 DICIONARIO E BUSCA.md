# E4 DICIONARIO E BUSCA

Os 535 códigos clínicos traduzidos e a busca sobre eles.

**Vocabulários:** SNOMED CT 272 · RxNorm 146 · LOINC 117 ·
134 códigos marcados com inconsistência de ETL

---

## HU-4.1 CONSULTAR O DICIONARIO DE CONCEITOS `MUST`

**Como** engenheiro, **quero** consultar o de-para dos códigos clínicos,
**para** entender o que cada código significa.

### Critérios de aceite

**API**
- [ ] `GET /dicionario` lista os 535 códigos, paginado
- [ ] Cada item: `codigo_origem`, `vocabulario`, `nome_portugues`,
      `dominios`, `ocorrencias`, `observacao`
- [ ] Filtros: `vocabulario`, `dominio`, `q` (busca textual)
- [ ] `GET /dicionario/{codigo}` retorna um código específico
- [ ] Códigos com inconsistência de ETL trazem a `observacao` preenchida (134)
- [ ] `404` para código inexistente

**UI**
- [ ] Tabela com busca e filtro por vocabulário
- [ ] Badge visual nos 134 códigos com inconsistência
- [ ] Coluna de ocorrências ordenável

### Armadilhas
As traduções **não têm fonte auditável** — foram feitas a partir dos códigos,
sem o `CONCEPT.csv` do Athena (ADR-001). A UI deve informar isso: para uso
clínico, validar contra o Athena.

### Dependências
Modelo de `dicionario_conceitos` · HU-5.4

---

## HU-4.2 BUSCAR CONDICOES MEDICAMENTOS E EXAMES POR NOME `MUST`

**Como** pesquisador, **quero** buscar um termo clínico em português,
**para** montar filtros sem saber o código.

### Critérios de aceite

**API**
- [ ] `GET /busca?q=diabet` retorna correspondências nos nomes clínicos
- [ ] Busca **case-insensitive e insensível a acento** — "diabetes" acha
      "Diabetes mellitus tipo 2"
- [ ] Resultados agrupados por domínio: condição, medicamento, procedimento,
      exame, observação
- [ ] Cada resultado traz nome, domínio, código e número de ocorrências
- [ ] Mínimo de 2 caracteres; abaixo disso, `400`
- [ ] Limite de resultados por domínio, com indicação de truncamento

**UI**
- [ ] Campo de busca com resultados agrupados por domínio
- [ ] Debounce — não dispara por tecla
- [ ] Clicar num resultado aplica como filtro na tela de origem
- [ ] Estado vazio sugere termos próximos quando não houver resultado

### Armadilhas
O banco usa `--locale=C` (ADR-002), então `ILIKE` não normaliza acento
automaticamente. Use `unaccent` ou normalize na aplicação — "obesidade" precisa
achar "Obesidade", e "pre-diabetes" precisa achar "Pré-diabetes".

### Dependências
HU-4.1 · ADR-002 (locale), ADR-006

---

## HU-4.3 AUTOCOMPLETE NOS FILTROS CLINICOS `SHOULD`

**Como** pesquisador, **quero** autocomplete ao filtrar por condição ou
medicamento, **para** não digitar o nome exato.

### Critérios de aceite

**API**
- [ ] `GET /dicionario/sugestoes?q=&dominio=` retorna até 10 sugestões
- [ ] Ordenadas por número de ocorrências — o mais comum primeiro
- [ ] Resposta mínima: apenas nome e código, para ser rápida

**UI**
- [ ] Autocomplete nos filtros de condição e medicamento (HU-1.1, HU-3.3)
- [ ] Navegação por teclado (setas, enter, esc)
- [ ] Seleção múltipla nos filtros que aceitam

### Dependências
HU-4.2, HU-3.3
