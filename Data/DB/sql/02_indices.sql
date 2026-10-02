-- Índices criados APÓS a carga (ver scripts/popular_banco.py), mas mantidos aqui
-- para que uma subida limpa do container já deixe o banco pronto caso a carga
-- seja feita por outro caminho. São idempotentes.
SET search_path TO synthea, public;

CREATE INDEX IF NOT EXISTS ix_atendimento_pessoa      ON atendimento(id_pessoa);
CREATE INDEX IF NOT EXISTS ix_atendimento_data        ON atendimento(data_inicio);

CREATE INDEX IF NOT EXISTS ix_condicao_pessoa         ON condicao(id_pessoa);
CREATE INDEX IF NOT EXISTS ix_condicao_atendimento    ON condicao(id_atendimento);
CREATE INDEX IF NOT EXISTS ix_condicao_conceito       ON condicao(id_conceito_condicao);
CREATE INDEX IF NOT EXISTS ix_condicao_nome           ON condicao(nome_condicao);
CREATE INDEX IF NOT EXISTS ix_condicao_data           ON condicao(data_inicio);

CREATE INDEX IF NOT EXISTS ix_medicamento_pessoa      ON exposicao_medicamento(id_pessoa);
CREATE INDEX IF NOT EXISTS ix_medicamento_atendimento ON exposicao_medicamento(id_atendimento);
CREATE INDEX IF NOT EXISTS ix_medicamento_nome        ON exposicao_medicamento(nome_medicamento);
-- consultas de medicamento quase sempre filtram as linhas com bug de ETL
CREATE INDEX IF NOT EXISTS ix_medicamento_validos     ON exposicao_medicamento(id_pessoa)
    WHERE inconsistencia_vocabulario IS NULL;

CREATE INDEX IF NOT EXISTS ix_procedimento_pessoa     ON procedimento(id_pessoa);
CREATE INDEX IF NOT EXISTS ix_procedimento_atendimento ON procedimento(id_atendimento);
CREATE INDEX IF NOT EXISTS ix_procedimento_nome       ON procedimento(nome_procedimento);

CREATE INDEX IF NOT EXISTS ix_exame_pessoa            ON exame(id_pessoa);
CREATE INDEX IF NOT EXISTS ix_exame_atendimento       ON exame(id_atendimento);
CREATE INDEX IF NOT EXISTS ix_exame_nome              ON exame(nome_exame);
CREATE INDEX IF NOT EXISTS ix_exame_data              ON exame(data);

CREATE INDEX IF NOT EXISTS ix_observacao_pessoa       ON observacao(id_pessoa);
CREATE INDEX IF NOT EXISTS ix_observacao_nome         ON observacao(nome_observacao);

CREATE INDEX IF NOT EXISTS ix_periodo_obs_pessoa      ON periodo_observacao(id_pessoa);
CREATE INDEX IF NOT EXISTS ix_periodo_cond_pessoa     ON periodo_condicao(id_pessoa);
CREATE INDEX IF NOT EXISTS ix_periodo_med_pessoa      ON periodo_medicamento(id_pessoa);

-- IDs originais das 3 tabelas com duplicatas no dataset Synthea: indexados para
-- lookup, mas sem UNIQUE porque o dataset repete valores (ver 01_schema.sql).
CREATE INDEX IF NOT EXISTS ix_medicamento_id_origem ON exposicao_medicamento(id_exposicao_medicamento);
CREATE INDEX IF NOT EXISTS ix_exame_id_origem       ON exame(id_exame);
CREATE INDEX IF NOT EXISTS ix_observacao_id_origem  ON observacao(id_observacao);
