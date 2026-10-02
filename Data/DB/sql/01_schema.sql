-- Schema OMOP CDM (nomes em português) para o dataset Synthea traduzido.
-- Executado automaticamente pelo postgres na primeira subida do container.

CREATE SCHEMA IF NOT EXISTS synthea;
SET search_path TO synthea, public;

-- ---------------------------------------------------------------- dimensões

CREATE TABLE pessoa (
    id_pessoa                   INTEGER PRIMARY KEY,
    id_conceito_sexo            INTEGER,
    ano_nascimento              INTEGER,
    mes_nascimento              INTEGER,
    dia_nascimento              INTEGER,
    data_hora_nascimento        TIMESTAMP,
    id_conceito_raca            INTEGER,
    id_conceito_etnia           INTEGER,
    id_local                    INTEGER,
    id_profissional             INTEGER,
    id_unidade_saude            INTEGER,
    codigo_origem_pessoa        TEXT,
    sexo                        TEXT,
    id_conceito_origem_sexo     INTEGER,
    raca                        TEXT,
    id_conceito_origem_raca     INTEGER,
    etnia                       TEXT,
    id_conceito_origem_etnia    INTEGER,
    sexo_descricao              TEXT,
    raca_descricao              TEXT
);

CREATE TABLE periodo_observacao (
    id_periodo_observacao       INTEGER PRIMARY KEY,
    id_pessoa                   INTEGER NOT NULL REFERENCES pessoa(id_pessoa),
    data_inicio_periodo         DATE,
    data_fim_periodo            DATE,
    id_conceito_tipo_periodo    INTEGER
);

CREATE TABLE atendimento (
    id_atendimento                  INTEGER PRIMARY KEY,
    id_pessoa                       INTEGER NOT NULL REFERENCES pessoa(id_pessoa),
    id_conceito_atendimento         INTEGER,
    data_inicio                     DATE,
    data_hora_inicio                TIMESTAMP,
    data_fim                        DATE,
    data_hora_fim                   TIMESTAMP,
    id_conceito_tipo_atendimento    INTEGER,
    id_profissional                 INTEGER,
    id_unidade_saude                INTEGER,
    codigo_origem_atendimento       TEXT,
    id_conceito_origem_atendimento  INTEGER,
    id_conceito_origem_admissao     INTEGER,
    origem_admissao                 TEXT,
    id_conceito_destino_alta        INTEGER,
    destino_alta                    TEXT,
    id_atendimento_anterior         INTEGER,
    atendimento_descricao           TEXT
);

-- ------------------------------------------------------------------ fatos

CREATE TABLE condicao (
    id_condicao                     INTEGER PRIMARY KEY,
    id_pessoa                       INTEGER NOT NULL REFERENCES pessoa(id_pessoa),
    id_conceito_condicao            INTEGER,
    data_inicio                     DATE,
    data_hora_inicio                TIMESTAMP,
    data_fim                        DATE,
    data_hora_fim                   TIMESTAMP,
    id_conceito_tipo_condicao       INTEGER,
    motivo_interrupcao              TEXT,
    id_profissional                 INTEGER,
    id_atendimento                  INTEGER REFERENCES atendimento(id_atendimento),
    id_detalhe_atendimento          INTEGER,
    codigo_origem_condicao          TEXT,
    id_conceito_origem_condicao     INTEGER,
    situacao_condicao               TEXT,
    id_conceito_situacao            INTEGER,
    nome_condicao                   TEXT
);

-- NOTA: id_exposicao_medicamento NAO e unico no dataset original (7.899 ids
-- repetidos apontando para registros clinicos distintos - bug de ETL do Synthea).
-- Usamos uma chave substituta e preservamos o id original como coluna comum.
CREATE TABLE exposicao_medicamento (
    pk                              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_exposicao_medicamento        INTEGER NOT NULL,
    id_pessoa                       INTEGER NOT NULL REFERENCES pessoa(id_pessoa),
    id_conceito_medicamento         INTEGER,
    data_inicio                     DATE,
    data_hora_inicio                TIMESTAMP,
    data_fim                        DATE,
    data_hora_fim                   TIMESTAMP,
    data_fim_literal                DATE,
    id_conceito_tipo_medicamento    INTEGER,
    motivo_interrupcao              TEXT,
    reposicoes                      INTEGER,
    quantidade                      NUMERIC,
    dias_fornecimento               INTEGER,
    posologia                       TEXT,
    id_conceito_via                 INTEGER,
    numero_lote                     TEXT,
    id_profissional                 INTEGER,
    id_atendimento                  INTEGER REFERENCES atendimento(id_atendimento),
    id_detalhe_atendimento          INTEGER,
    codigo_origem_medicamento       TEXT,
    id_conceito_origem_medicamento  INTEGER,
    via_administracao               TEXT,
    unidade_dose                    TEXT,
    nome_medicamento                TEXT,
    -- marca as linhas em que o codigo-fonte e SNOMED de condicao (bug de ETL
    -- do dataset original). NULL = medicamento RxNorm valido.
    inconsistencia_vocabulario      TEXT
);

CREATE TABLE procedimento (
    id_procedimento                 INTEGER PRIMARY KEY,
    id_pessoa                       INTEGER NOT NULL REFERENCES pessoa(id_pessoa),
    id_conceito_procedimento        INTEGER,
    data                            DATE,
    data_hora                       TIMESTAMP,
    id_conceito_tipo_procedimento   INTEGER,
    id_conceito_modificador         INTEGER,
    quantidade                      NUMERIC,
    id_profissional                 INTEGER,
    id_atendimento                  INTEGER REFERENCES atendimento(id_atendimento),
    id_detalhe_atendimento          INTEGER,
    codigo_origem_procedimento      TEXT,
    id_conceito_origem_procedimento INTEGER,
    modificador                     TEXT,
    nome_procedimento               TEXT
);

-- NOTA: id_exame NAO e unico no dataset original (29.471 ids repetidos).
CREATE TABLE exame (
    pk                              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_exame                        INTEGER NOT NULL,
    id_pessoa                       INTEGER NOT NULL REFERENCES pessoa(id_pessoa),
    id_conceito_exame               INTEGER,
    data                            DATE,
    data_hora                       TIMESTAMP,
    hora                            TEXT,
    id_conceito_tipo_exame          INTEGER,
    id_conceito_operador            INTEGER,
    -- ATENCAO: 100% NULL no dataset original (resultados perdidos no ETL)
    valor_numerico                  NUMERIC,
    id_conceito_valor               INTEGER,
    id_conceito_unidade             INTEGER,
    limite_inferior                 NUMERIC,
    limite_superior                 NUMERIC,
    id_profissional                 INTEGER,
    id_atendimento                  INTEGER REFERENCES atendimento(id_atendimento),
    id_detalhe_atendimento          INTEGER,
    codigo_origem_exame             TEXT,
    id_conceito_origem_exame        INTEGER,
    unidade                         TEXT,
    valor_origem                    TEXT,
    nome_exame                      TEXT
);

-- NOTA: id_observacao NAO e unico no dataset original (619 ids repetidos).
CREATE TABLE observacao (
    pk                              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_observacao                   INTEGER NOT NULL,
    id_pessoa                       INTEGER NOT NULL REFERENCES pessoa(id_pessoa),
    id_conceito_observacao          INTEGER,
    data                            DATE,
    data_hora                       TIMESTAMP,
    id_conceito_tipo_observacao     INTEGER,
    valor_numerico                  NUMERIC,
    valor_texto                     TEXT,
    id_conceito_valor               INTEGER,
    id_conceito_qualificador        INTEGER,
    id_conceito_unidade             INTEGER,
    id_profissional                 INTEGER,
    id_atendimento                  INTEGER REFERENCES atendimento(id_atendimento),
    id_detalhe_atendimento          INTEGER,
    codigo_origem_observacao        TEXT,
    id_conceito_origem_observacao   INTEGER,
    unidade                         TEXT,
    qualificador                    TEXT,
    nome_observacao                 TEXT
);

-- ---------------------------------------------------------------- períodos

CREATE TABLE periodo_condicao (
    id_periodo_condicao         INTEGER PRIMARY KEY,
    id_pessoa                   INTEGER NOT NULL REFERENCES pessoa(id_pessoa),
    id_conceito_condicao        INTEGER,
    data_inicio                 DATE,
    data_fim                    DATE,
    contagem_ocorrencias        INTEGER
);

CREATE TABLE periodo_medicamento (
    id_periodo_medicamento      INTEGER PRIMARY KEY,
    id_pessoa                   INTEGER NOT NULL REFERENCES pessoa(id_pessoa),
    id_conceito_medicamento     INTEGER,
    data_inicio                 DATE,
    data_fim                    DATE,
    contagem_exposicoes         INTEGER,
    dias_intervalo              INTEGER
);

-- -------------------------------------------------------------- dicionário

CREATE TABLE dicionario_conceitos (
    codigo_origem       TEXT PRIMARY KEY,
    vocabulario         TEXT,
    nome_portugues      TEXT,
    dominios            TEXT,
    ocorrencias         INTEGER,
    observacao          TEXT
);
