# E3 COORTES E ESTATISTICAS

Visão populacional sobre os 1.130 pacientes.

**Dados relevantes:** 247 pacientes com multimorbidade (2+ crônicas) ·
134 condições distintas · 145 medicamentos válidos

---

## HU-3.1 DASHBOARD POPULACIONAL `MUST`

**Como** pesquisador, **quero** uma visão geral da base,
**para** entender a população antes de investigar.

### Critérios de aceite

**API**
- [ ] `GET /estatisticas/resumo` devolve todos os números-chave em **uma** chamada
- [ ] Inclui: total de pacientes, distribuição por sexo e raça, pirâmide etária
      em faixas de 10 anos, atendimentos por tipo
- [ ] Inclui contagem de multimorbidade (**247** com 2+ crônicas)
- [ ] Declara a janela temporal coberta (1909-2019)
- [ ] Resposta cacheável — os dados não mudam
- [ ] Agregações em SQL direto, não ORM (ADR-006)

**UI**
- [ ] Cards com os números principais
- [ ] Gráficos de distribuição demográfica e de atendimentos
- [ ] Gráficos legíveis em tema claro **e** escuro
- [ ] Nota sobre o viés da população (75% branca, Massachusetts)

### Armadilhas
**Nenhum gráfico de valor de exame** — o dado não existe (ADR-008). A tentação
de incluir "média de pressão arterial" é real e impossível.

A janela de 1909-2019 significa que gráficos temporais têm uma cauda longa e
esparsa no início. Considere cortar em 1950 ou usar escala adequada.

### Dependências
ADR-008

---

## HU-3.2 PREVALENCIA DE CONDICOES `MUST`

**Como** pesquisador, **quero** a prevalência das condições,
**para** saber o que é comum nesta população.

### Critérios de aceite

**API**
- [ ] `GET /estatisticas/condicoes` lista as **134** condições com contagem de
      ocorrências **e** de pacientes distintos (consulta em SQL direto — ADR-006)
- [ ] Corte opcional por `sexo`, `raca`, `idade_min`, `idade_max`
- [ ] Ordenável por prevalência ou nome
- [ ] **Distingue ocorrências de pacientes afetados** — um paciente pode ter a
      mesma condição várias vezes
- [ ] Resposta inclui o denominador usado no cálculo

**UI**
- [ ] Barras horizontais ordenadas por prevalência
- [ ] Filtros demográficos aplicáveis ao vivo
- [ ] Exibe ambas as métricas: ocorrências e pacientes
- [ ] Clicar numa condição abre a coorte correspondente (HU-3.3)

### Armadilhas
Confundir ocorrência com paciente é o erro mais fácil aqui. Exemplo real:
"Infecção viral das vias aéreas superiores" tem 1.134 ocorrências em **711
pacientes**. Reportar 1.134 como prevalência estaria errado.

### Dependências
HU-3.1

---

## HU-3.3 CONSTRUTOR DE COORTES `MUST`

**Como** pesquisador, **quero** montar uma coorte combinando critérios,
**para** isolar o grupo que vou estudar.

### Critérios de aceite

**API**
- [ ] `POST /coortes` aceita critérios combinados: condições (E/OU),
      medicamentos, faixa de idade, sexo, raça, tipo de atendimento
- [ ] Retorna `total` e lista paginada de pacientes
- [ ] `GET /coortes/previa` devolve **só a contagem**, para feedback ao vivo
- [ ] Resposta declara **todos** os filtros aplicados, inclusive os de
      qualidade (nascimento implausível, medicamentos inválidos)
- [ ] Combinação sem resultado retorna `total: 0`, não erro
- [ ] Critérios validados: condição/medicamento inexistente retorna `400` com
      sugestão, não lista vazia silenciosa

**UI**
- [ ] Monta critérios incrementalmente, com o **N atualizado a cada mudança**
- [ ] Debounce na prévia — não dispara request por tecla
- [ ] Mostra quais filtros de qualidade estão ativos
- [ ] Botão para abrir a coorte como lista de pacientes
- [ ] Critérios na URL — coorte compartilhável

### Armadilhas
É o endpoint com mais filtros dinâmicos — e o motivo principal de adotar ORM
(ADR-006). A composição condicional de `where()` elimina o risco de injection
que a concatenação de string traria. **Nunca** monte este `WHERE` por string.

Ordenação dinâmica mapeada a atributo do modelo, nunca a nome de coluna vindo
do cliente.

A prévia é chamada a cada interação — garanta o índice e cancele requests
obsoletos no cliente.

### Dependências
HU-1.1, HU-3.2, HU-5.4 · ADR-006

---

## HU-3.4 EXPORTAR COORTE `SHOULD`

**Como** pesquisador, **quero** exportar a coorte em CSV,
**para** analisar fora do sistema.

### Critérios de aceite

**API**
- [ ] `GET /coortes/exportar` devolve CSV
- [ ] **Cabeçalho do arquivo documenta os critérios** e os filtros de qualidade
- [ ] Colunas: `id_pessoa`, `codigo_origem_pessoa` (UUID), demografia, contadores
- [ ] Nome do arquivo com data e hora
- [ ] Limite de linhas documentado; acima dele, erro explicativo
- [ ] Encoding UTF-8 com BOM, para abrir corretamente no Excel

**UI**
- [ ] Botão de exportar na tela de coorte
- [ ] Indicação de progresso para exportações grandes

### Armadilhas
Inclua o **UUID**, não só o `id_pessoa`: o ID é sequencial e específico desta
carga, enquanto o UUID é o identificador estável para cruzar com outra fonte
(ADR-009).

### Dependências
HU-3.3

---

## HU-3.5 TOP MEDICAMENTOS PROCEDIMENTOS E EXAMES `SHOULD`

**Como** pesquisador, **quero** os rankings por domínio,
**para** ver o que mais acontece nesta população.

### Critérios de aceite

**API**
- [ ] `GET /estatisticas/medicamentos` — os **145** medicamentos válidos;
      resposta informa que **7.899** registros foram excluídos e por quê
- [ ] `GET /estatisticas/procedimentos` — os **91** procedimentos
- [ ] `GET /estatisticas/exames` — os **240** exames, marcados sem resultado
- [ ] Todos com corte demográfico opcional
- [ ] Todos distinguem ocorrências de pacientes distintos

**UI**
- [ ] Três listas em abas
- [ ] Nota de rodapé nos medicamentos sobre os excluídos
- [ ] Aviso na aba de exames: frequência de pedido, não resultado

### Armadilhas
Sem o filtro, o topo da lista de medicamentos seria **"Infecção viral das vias
aéreas superiores"** — um diagnóstico. É o sintoma mais visível do bug de ETL
(ADR-008).

### Dependências
HU-3.1 · ADR-008
