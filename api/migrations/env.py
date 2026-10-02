"""Ambiente do Alembic.

Dois pontos não óbvios (ADR-006):
  - include_schemas=True, porque as tabelas vivem no schema `synthea`
  - as views são EXCLUÍDAS do autogenerate; sem isso o Alembic tenta criá-las
    como tabela
"""
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool, text

from api.config import obter_configuracao
from api.modelos import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

cfg = obter_configuracao()
config.set_main_option("sqlalchemy.url", cfg.url_banco_sincrona)

target_metadata = Base.metadata

# nomes das views mapeadas como modelo — não são tabelas gerenciadas
VIEWS = {"vw_pessoa_valida", "vw_medicamento_valido", "vw_atendimento_resumo"}


def incluir_objeto(objeto, nome, tipo, reflexivo, comparar_com):
    """Mantém as views fora do autogenerate (ADR-006)."""
    if tipo == "table" and nome in VIEWS:
        return False
    return True


def executar_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        include_schemas=True,
        version_table_schema=cfg.schema_dados,
        include_object=incluir_objeto,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def executar_online() -> None:
    conectavel = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with conectavel.connect() as conexao:
        # a tabela de versão vive no schema de dados, que precisa existir antes
        # de a primeira migration rodar
        conexao.execute(text(f"CREATE SCHEMA IF NOT EXISTS {cfg.schema_dados}"))
        conexao.commit()

        context.configure(
            connection=conexao,
            target_metadata=target_metadata,
            include_schemas=True,
            version_table_schema=cfg.schema_dados,
            include_object=incluir_objeto,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    executar_offline()
else:
    executar_online()
