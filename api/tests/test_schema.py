"""Garante que as DUAS fontes de schema concordam (HU-5.5).

O schema existe em dois lugares (ADR-002, ADR-006):
  - Data/DB/sql/01_schema.sql + 02_indices.sql — bootstrap do container
  - api/migrations/ — migrations Alembic

Divergência entre eles é o risco mais provável do projeto: o ambiente de
desenvolvimento passaria a diferir do que as migrations produzem, sem erro
visível. Este teste é o que impede isso.

Os bancos temporários são criados e destruídos pelo próprio teste.
"""
import subprocess
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
CONTAINER = "agentic-health-db"
BD_MIGRATION = "teste_schema_migration"
BD_BOOTSTRAP = "teste_schema_bootstrap"


def _psql(banco: str, sql: str, *, tuplas_apenas: bool = True) -> str:
    cmd = ["docker", "exec", CONTAINER, "psql", "-U", "postgres", "-d", banco]
    if tuplas_apenas:
        cmd += ["-t", "-A"]
    cmd += ["-c", sql]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        pytest.fail(f"psql falhou em {banco}: {r.stderr[:400]}")
    return r.stdout


def _admin(sql: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["docker", "exec", CONTAINER, "psql", "-U", "postgres", "-q", "-c", sql],
        capture_output=True,
        text=True,
    )


def _docker_disponivel() -> bool:
    r = subprocess.run(
        ["docker", "exec", CONTAINER, "true"], capture_output=True, text=True
    )
    return r.returncode == 0


pytestmark = pytest.mark.skipif(
    not _docker_disponivel(), reason=f"container {CONTAINER} não está acessível"
)


@pytest.fixture(scope="module")
def bancos_comparaveis() -> tuple[str, str]:
    """Cria um banco pela migration e outro pelo SQL de bootstrap."""
    for banco in (BD_MIGRATION, BD_BOOTSTRAP):
        _admin(f"DROP DATABASE IF EXISTS {banco}")
        _admin(f"CREATE DATABASE {banco}")

    # 1) via Alembic
    r = subprocess.run(
        ["python3", "-m", "alembic", "upgrade", "head"],
        cwd=RAIZ / "api",
        capture_output=True,
        text=True,
        env={**__import__("os").environ, "POSTGRES_DB": BD_MIGRATION},
    )
    if r.returncode != 0:
        pytest.fail(f"alembic upgrade falhou: {r.stderr[-600:]}")

    # 2) via SQL de bootstrap
    for arquivo in ("01_schema.sql", "02_indices.sql"):
        caminho = RAIZ / "Data" / "DB" / "sql" / arquivo
        proc = subprocess.run(
            ["docker", "exec", "-i", CONTAINER, "psql", "-U", "postgres",
             "-d", BD_BOOTSTRAP, "-q", "-v", "ON_ERROR_STOP=1"],
            input=caminho.read_text(encoding="utf-8"),
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            pytest.fail(f"{arquivo} falhou: {proc.stderr[-400:]}")

    yield BD_MIGRATION, BD_BOOTSTRAP

    for banco in (BD_MIGRATION, BD_BOOTSTRAP):
        _admin(f"DROP DATABASE IF EXISTS {banco}")


def _colunas(banco: str) -> set[str]:
    saida = _psql(
        banco,
        """SELECT table_name||'.'||column_name||' '||data_type||' '||is_nullable
             FROM information_schema.columns
            WHERE table_schema='synthea' AND table_name <> 'alembic_version'
            ORDER BY 1""",
    )
    return {linha.strip() for linha in saida.splitlines() if linha.strip()}


def _indices(banco: str) -> set[str]:
    saida = _psql(
        banco,
        """SELECT indexname||' | '||indexdef FROM pg_indexes
            WHERE schemaname='synthea' AND tablename <> 'alembic_version'
            ORDER BY 1""",
    )
    return {linha.strip() for linha in saida.splitlines() if linha.strip()}


def test_migration_e_bootstrap_tem_as_mesmas_colunas(bancos_comparaveis):
    bd_mig, bd_boot = bancos_comparaveis
    cols_mig, cols_boot = _colunas(bd_mig), _colunas(bd_boot)

    assert cols_mig, "a migration não criou nenhuma coluna"
    assert cols_mig == cols_boot, (
        "Schema da migration divergiu do SQL de bootstrap.\n"
        f"Só na migration: {sorted(cols_mig - cols_boot)}\n"
        f"Só no bootstrap: {sorted(cols_boot - cols_mig)}"
    )


def test_migration_e_bootstrap_tem_os_mesmos_indices(bancos_comparaveis):
    bd_mig, bd_boot = bancos_comparaveis
    idx_mig, idx_boot = _indices(bd_mig), _indices(bd_boot)

    assert idx_mig, "a migration não criou nenhum índice"
    assert idx_mig == idx_boot, (
        "Índices da migration divergiram do SQL de bootstrap.\n"
        f"Só na migration: {sorted(idx_mig - idx_boot)}\n"
        f"Só no bootstrap: {sorted(idx_boot - idx_mig)}"
    )


def test_chave_substituta_e_pk_nos_dois_schemas(bancos_comparaveis):
    """Nas 3 tabelas com ID duplicado, `pk` é a primary key (ADR-002)."""
    for banco in bancos_comparaveis:
        for tabela in ("exame", "exposicao_medicamento", "observacao"):
            saida = _psql(
                banco,
                f"""SELECT a.attname
                      FROM pg_index i
                      JOIN pg_attribute a
                        ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey)
                     WHERE i.indrelid = 'synthea.{tabela}'::regclass
                       AND i.indisprimary""",
            )
            pks = {l.strip() for l in saida.splitlines() if l.strip()}
            assert pks == {"pk"}, (
                f"{banco}.{tabela}: PK deveria ser 'pk', veio {pks}"
            )


def test_alembic_check_nao_detecta_divergencia():
    """Os modelos ORM batem com o banco de desenvolvimento (ADR-006)."""
    r = subprocess.run(
        ["python3", "-m", "alembic", "check"],
        cwd=RAIZ / "api",
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, (
        "Modelos ORM divergem do banco. Saída do alembic check:\n"
        f"{(r.stdout + r.stderr)[-1500:]}"
    )
