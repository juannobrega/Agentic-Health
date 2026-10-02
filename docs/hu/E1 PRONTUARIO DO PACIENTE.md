# E1 PRONTUARIO DO PACIENTE

A tela central do produto: a história clínica completa de um paciente.

**Dados disponíveis:** 1.130 pacientes · 134 condições distintas ·
145 medicamentos válidos · 91 procedimentos · 240 exames · 619 alergias

---

## HU-1.1 LISTAR PACIENTES COM FILTROS `MUST`

**Como** clínico, **quero** navegar a lista de pacientes com filtros,
**para** encontrar os casos que me interessam.

### Critérios de aceite

**API**
- [ ] `GET /pacientes` retorna lista paginada — default 25, máximo 100
- [ ] Filtros combináveis: `sexo`, `raca`, `etnia`, `idade_min`, `idade_max`, `condicao`
- [ ] Resposta traz `total`, `pagina`, `por_pagina` e `itens`
- [ ] Cada item: `id_pessoa`, `codigo_origem_pessoa`, `sexo`, `idade`, `raca`,
      `etnia` e contadores por domínio
- [ ] Por padrão exclui os 2 pacientes com nascimento implausível → retorna
      **1.128 de 1.130**; `incluir_invalidos=true` traz os dois de volta
- [ ] Ordenação por `id_pessoa` ou `idade`, `asc`/`desc`, mapeada a atributo do modelo
- [ ] `400` com mensagem clara para coluna de ordenação inválida

**UI**
- [ ] Tabela com filtros laterais e paginação no rodapé
- [ ] Rótulo de cada paciente: `Paciente #<id> · <sexo>, <idade> anos`
- [ ] Filtros refletidos na URL (`?sexo=F&idade_min=40`) — view compartilhável
- [ ] Placeholder da busca: "Buscar por ID ou UUID" — nunca "nome"
- [ ] Estado vazio explica que nenhum paciente atende aos filtros

### Armadilhas
Sem busca por nome — o OMOP não tem esse campo (ADR-009). O filtro por
`condicao` exige join com `condicao`; use o índice em `nome_condicao`.

### Dependências
Modelo `PessoaValida` (view) · ADR-006 (ordenação por atributo) · ADR-009

---

## HU-1.2 VER DADOS DEMOGRAFICOS DO PACIENTE `MUST`

**Como** clínico, **quero** abrir um paciente e ver quem ele é,
**para** contextualizar a história clínica.

### Critérios de aceite

**API**
- [ ] `GET /pacientes/{id}` retorna demografia completa + `idade` calculada
- [ ] Inclui janela de observação (`data_inicio_periodo`, `data_fim_periodo`)
- [ ] Inclui contadores: condições, medicamentos válidos, procedimentos,
      exames, atendimentos, alergias
- [ ] `404` com mensagem clara para ID inexistente
- [ ] Paciente com nascimento implausível retorna o dado **com aviso** no payload,
      não erro — IDs 265 (2099) e 332 (1099)

**UI**
- [ ] Cabeçalho com ID, UUID, sexo, idade, raça/etnia e janela de observação
- [ ] UUID copiável com um clique
- [ ] Aviso visível quando o ano de nascimento é implausível
- [ ] Contadores como atalhos para as abas correspondentes

### Dependências
`vw_pessoa_valida` · HU-1.1

---

## HU-1.3 TIMELINE CLINICA UNIFICADA `MUST`

**Como** clínico, **quero** ver todos os eventos do paciente numa linha do tempo,
**para** entender a evolução sem pular entre abas.

### Critérios de aceite

**API**
- [ ] `GET /pacientes/{id}/timeline` unifica condições, medicamentos,
      procedimentos e exames ordenados por data
- [ ] Cada evento: `tipo`, `data`, `nome`, `id_atendimento`, `codigo_origem`, `pk`
- [ ] Filtros: `tipo` (múltiplo), `data_de`, `data_ate`
- [ ] **Paginada** — o paciente 736 tem 2.486 exames
- [ ] Medicamentos filtrados pelo modelo `MedicamentoValido` (a view)
- [ ] Eventos de exame trazem `valor_disponivel: false` (ADR-008)
- [ ] Resposta declara os filtros de qualidade aplicados

**UI**
- [ ] Timeline vertical com ícone e cor por tipo de evento
- [ ] Agrupamento por ano, com contagem por tipo no cabeçalho do grupo
- [ ] **Lista virtualizada** — renderizar 2.486 itens de uma vez congela a aba
- [ ] Clicar num evento abre o atendimento correspondente
- [ ] Filtro por tipo como chips alternáveis
- [ ] Exames exibem "sem resultado disponível", não valor vazio

### Armadilhas
Endpoint mais valioso do épico — hoje isso exigiria 4 queries e conhecer as
ressalvas. Benchmark de referência: a query union roda em **0,24ms** no paciente
736. Se passar disso, verifique os índices.

### Dependências
ADR-002 e ADR-006 (`pk`) · ADR-008 (exames sem valor) · ADR-007 (virtualização)

---

## HU-1.4 ABAS DE DETALHE POR DOMINIO `MUST`

**Como** clínico, **quero** ver condições, medicamentos, procedimentos e exames
em listas próprias, **para** analisar um domínio de cada vez.

### Critérios de aceite

**API**
- [ ] `GET /pacientes/{id}/condicoes` — nome, data início/fim, atendimento
- [ ] `GET /pacientes/{id}/medicamentos` — nome, período, dias de fornecimento;
      resposta inclui `excluidos_por_qualidade` e o motivo
- [ ] `GET /pacientes/{id}/procedimentos` — nome, data, atendimento
- [ ] `GET /pacientes/{id}/exames` — nome, data, `valor_disponivel: false`
- [ ] Todas paginadas e ordenáveis por data
- [ ] Todas retornam `pk` como identificador do registro

**UI**
- [ ] Abas com contador em cada uma
- [ ] Coluna de valor dos exames: "não disponível" com estilo discreto
- [ ] Nota de rodapé nos medicamentos informando quantos foram excluídos e por quê
- [ ] Ordenação por data clicável no cabeçalho

### Dependências
HU-1.2 · ADR-008

---

## HU-1.5 ALERGIAS EM DESTAQUE `SHOULD`

**Como** clínico, **quero** ver as alergias do paciente com destaque,
**para** não prescrever algo contraindicado.

### Critérios de aceite

**API**
- [ ] `GET /pacientes/{id}/alergias` filtra as observações de alergia
      (619 no total da base)
- [ ] Retorna nome da alergia, data de registro e `pk`
- [ ] Lista vazia (não `404`) para paciente sem alergia

**UI**
- [ ] Alergias como alerta fixo no cabeçalho do prontuário, não só na aba
- [ ] Paciente sem alergia **não** mostra alerta vazio
- [ ] Ícone e cor de atenção, sem alarmismo visual

### Armadilhas
O filtro é por `nome_observacao LIKE 'Alergia%'` — `observacao` tem 83% de
`concept_id = 0`, então filtrar por conceito não funciona (ADR-001).

### Dependências
HU-1.2

---

## HU-1.6 RESUMO CLINICO EM TEXTO `SHOULD`

**Como** clínico, **quero** um resumo em texto do prontuário,
**para** ler rápido e copiar para outro sistema.

### Critérios de aceite

**API**
- [ ] `GET /pacientes/{id}/resumo` devolve texto corrido em português
- [ ] Cobre: demografia, condições, medicamentos ativos, alergias e
      últimos atendimentos
- [ ] **Declara explicitamente** que exames não têm resultados disponíveis
- [ ] Texto gerado por **template determinístico**, nunca por LLM
- [ ] Mesma entrada produz exatamente a mesma saída

**UI**
- [ ] Botão de copiar o texto
- [ ] Monoespaçado, preservando quebras de linha

### Armadilhas
O resumo deve dizer o que **não** se sabe, não só o que se sabe: sem a menção
explícita aos exames sem resultado, quem lê conclui que não houve alteração
(ADR-008).

Gerá-lo com LLM introduziria alucinação num texto que precisa ser factual —
por isso é template determinístico.

### Dependências
HU-1.2, HU-1.4, HU-1.5 · ADR-008
