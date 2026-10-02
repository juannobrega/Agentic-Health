-- Views de conveniência: aplicam os filtros de qualidade documentados no
-- README do dataset, para não repetir as mesmas ressalvas em cada consulta.
SET search_path TO synthea, public;

-- Pacientes com ano de nascimento plausível (exclui 2 registros impossíveis:
-- id_pessoa 265 com 2099 e 332 com 1099).
CREATE OR REPLACE VIEW vw_pessoa_valida AS
SELECT *,
       EXTRACT(YEAR FROM CURRENT_DATE)::int - ano_nascimento AS idade
FROM pessoa
WHERE ano_nascimento BETWEEN 1900 AND EXTRACT(YEAR FROM CURRENT_DATE)::int;

-- Somente medicamentos de verdade: exclui as 7.899 linhas cujo código-fonte é
-- SNOMED de condição em vez de RxNorm (bug de ETL do Synthea original).
CREATE OR REPLACE VIEW vw_medicamento_valido AS
SELECT *
FROM exposicao_medicamento
WHERE inconsistencia_vocabulario IS NULL;

-- Visão clínica achatada por atendimento, já em português.
CREATE OR REPLACE VIEW vw_atendimento_resumo AS
SELECT a.id_atendimento,
       a.id_pessoa,
       p.sexo,
       p.raca,
       a.data_inicio,
       a.atendimento_descricao,
       (SELECT count(*) FROM condicao c              WHERE c.id_atendimento = a.id_atendimento) AS qtd_condicoes,
       (SELECT count(*) FROM procedimento pr         WHERE pr.id_atendimento = a.id_atendimento) AS qtd_procedimentos,
       (SELECT count(*) FROM exame e                 WHERE e.id_atendimento = a.id_atendimento) AS qtd_exames,
       (SELECT count(*) FROM vw_medicamento_valido m WHERE m.id_atendimento = a.id_atendimento) AS qtd_medicamentos
FROM atendimento a
JOIN pessoa p ON p.id_pessoa = a.id_pessoa;
