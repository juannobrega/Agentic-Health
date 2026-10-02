# E2 ATENDIMENTOS E TRAJETORIA

Os 32.153 atendimentos e os 31.027 encadeamentos entre eles.

**Distribuição:** Ambulatorial 29.343 (91%) · Emergência 1.809 (5,6%) ·
Internação 1.001 (3,1%) · Média de 28,6 atendimentos por paciente, máximo 251

---

## HU-2.1 LISTAR ATENDIMENTOS `MUST`

**Como** clínico, **quero** filtrar atendimentos por tipo e período,
**para** analisar a utilização de serviço.

### Critérios de aceite

**API**
- [ ] `GET /atendimentos` paginado — default 25, máximo 100
- [ ] Filtros: `tipo`, `id_pessoa`, `data_de`, `data_ate`
- [ ] Cada item: `id_atendimento`, paciente, tipo, datas, duração em dias
- [ ] Ordenação por data, `asc`/`desc`
- [ ] `tipo` validado contra enum — Ambulatorial, Emergência, Internação

**UI**
- [ ] Tabela com filtro de tipo em destaque (chips com contagem)
- [ ] Filtros na URL
- [ ] Coluna de duração calculada, não bruta
- [ ] Link para o prontuário do paciente e para o detalhe do atendimento

### Armadilhas
A base cobre **1909 a 2019**. Um filtro de data com default "últimos 30 dias"
retornaria vazio — não assuma recência.

### Dependências
Modelo de `vw_atendimento_resumo` · HU-5.4 (modelos ORM)

---

## HU-2.2 DETALHE DO ATENDIMENTO `MUST`

**Como** clínico, **quero** abrir um atendimento e ver tudo que aconteceu nele,
**para** entender aquele episódio de cuidado.

### Critérios de aceite

**API**
- [ ] `GET /atendimentos/{id}` traz o atendimento e os dados do paciente
- [ ] Inclui as condições diagnosticadas, medicamentos prescritos,
      procedimentos realizados e exames pedidos **naquele** atendimento
- [ ] Medicamentos filtrados pelo modelo `MedicamentoValido` (a view)
- [ ] Link para o atendimento anterior quando `id_atendimento_anterior` existir
- [ ] `404` com mensagem clara para ID inexistente
- [ ] Atendimento sem eventos retorna listas vazias, não `404`

**UI**
- [ ] Seções por domínio, com contador em cada
- [ ] Navegação para o atendimento anterior, quando houver
- [ ] Exames com "sem resultado disponível"
- [ ] Seção vazia aparece colapsada, não omitida

### Armadilhas
Um atendimento chega a **97 exames** (medido). Pagine as seções ou colapse por
padrão quando passar de ~20 itens.

### Dependências
HU-2.1 · ADR-008

---

## HU-2.3 TRAJETORIA DO PACIENTE `SHOULD`

**Como** pesquisador, **quero** ver a sequência de atendimentos encadeados,
**para** estudar o percurso do paciente no sistema.

### Critérios de aceite

**API**
- [ ] `GET /pacientes/{id}/trajetoria` devolve os atendimentos em ordem,
      seguindo `id_atendimento_anterior`
- [ ] Cada passo: tipo, data, intervalo em dias desde o anterior, condições
- [ ] **Detecta ciclos** e cadeias quebradas sem entrar em loop infinito
- [ ] Limite máximo de passos, com indicação de truncamento
- [ ] Paciente sem encadeamento retorna os atendimentos em ordem cronológica

**UI**
- [ ] Sequência como fluxo horizontal navegável
- [ ] Intervalo entre atendimentos visível entre os nós
- [ ] Cor do nó por tipo de atendimento
- [ ] Clicar num passo abre o detalhe (HU-2.2)
- [ ] Aviso visual quando a cadeia foi truncada ou tem ciclo

### Armadilhas
**31.027 atendimentos têm predecessor** — a maioria. Teste com o paciente de 251
atendimentos: a recursão ingênua pode estourar. Use CTE recursiva com
`UNION` (não `UNION ALL`) ou limite de profundidade explícito.

Nada no dataset garante ausência de ciclo. Trate como grafo, não como lista.

Esta é uma das consultas que fica em **SQL direto** — recursão é desajeitada no
ORM (ADR-006).

### Dependências
HU-2.2 · ADR-006

---

## HU-2.4 REINTERNACOES `COULD`

**Como** pesquisador, **quero** identificar pacientes com internações repetidas,
**para** estudar readmissão.

### Critérios de aceite

**API**
- [ ] `GET /estatisticas/reinternacoes` lista os **78 pacientes** com mais de
      uma internação
- [ ] Para cada um: número de internações e intervalo entre elas
- [ ] Filtro opcional por janela máxima de dias entre internações
- [ ] Ordenação por número de internações ou menor intervalo

**UI**
- [ ] Tabela ordenável com link para o prontuário
- [ ] Destaque para intervalos curtos (readmissão precoce)

### Armadilhas
"Reinternação" aqui é apenas mais de uma internação no histórico — **não** é a
definição clínica de readmissão em 30 dias. Deixe isso explícito na tela para
não ser lido como indicador de qualidade assistencial.

### Dependências
HU-2.1
