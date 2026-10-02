#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Popula o Postgres com o dataset Synthea traduzido (Data/Synthea).

Usa COPY ... FROM STDIN (binário de texto) em vez de INSERT: as 311 mil linhas
entram em segundos. Converte '' -> NULL e normaliza os '0' que o OMOP usa como
sentinela de "sem referência" nas FKs opcionais.

Uso:
    python3 Data/DB/scripts/popular_banco.py              # carga completa
    python3 Data/DB/scripts/popular_banco.py --recriar    # dropa e recria o schema
    python3 Data/DB/scripts/popular_banco.py --verificar  # só valida o carregado
"""
from __future__ import annotations

import argparse
import csv
import os
import sys
import time
from pathlib import Path

try:
    import psycopg
except ImportError:
    sys.exit("psycopg não instalado. Rode:  pip install -r Data/DB/requirements.txt")

_RAIZ_PROJETO = Path(__file__).resolve().parents[3]   # .../Agentic Health

try:
    from dotenv import load_dotenv
    # .env unico, sempre na raiz do projeto
    load_dotenv(_RAIZ_PROJETO / ".env")
except ImportError:
    pass  # .env é opcional; variáveis de ambiente também servem

BASE  = Path(__file__).resolve().parent.parent      # Data/DB
DADOS = BASE.parent / "Synthea"                     # Data/Synthea
SCHEMA = "synthea"

# ordem importa: pessoa e atendimento antes das tabelas que os referenciam
TABELAS = [
    ("pessoa.csv",                "pessoa"),
    ("atendimento.csv",           "atendimento"),
    ("periodo_observacao.csv",    "periodo_observacao"),
    ("condicao.csv",              "condicao"),
    ("exposicao_medicamento.csv", "exposicao_medicamento"),
    ("procedimento.csv",          "procedimento"),
    ("exame.csv",                 "exame"),
    ("observacao.csv",            "observacao"),
    ("periodo_condicao.csv",      "periodo_condicao"),
    ("periodo_medicamento.csv",   "periodo_medicamento"),
    ("dicionario_conceitos.csv",  "dicionario_conceitos"),
]

# FKs opcionais onde o Synthea grava 0 em vez de vazio. 0 não existe como
# chave, então viraria violação de FK — convertemos para NULL.
FK_ZERO_E_NULO = {
    "id_atendimento", "id_detalhe_atendimento", "id_profissional",
    "id_unidade_saude", "id_local", "id_atendimento_anterior",
}

# colunas que o Postgres precisa receber como NULL quando vierem vazias
# (todo o resto é TEXT e aceita string vazia, mas preferimos NULL por consistência)
def limpar(valor: str, coluna: str) -> str | None:
    if valor == "":
        return None
    if coluna in FK_ZERO_E_NULO and valor == "0":
        return None
    return valor


def conectar() -> psycopg.Connection:
    return psycopg.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        dbname=os.getenv("POSTGRES_DB", "agentic_health"),
        user=os.getenv("POSTGRES_USER", "postgres"),
        password=os.getenv("POSTGRES_PASSWORD", "postgres"),
    )


def recriar_schema(conn: psycopg.Connection) -> None:
    print("Recriando schema…")
    with conn.cursor() as cur:
        cur.execute(f"DROP SCHEMA IF EXISTS {SCHEMA} CASCADE")
    for arquivo in ("01_schema.sql", "02_indices.sql", "03_views.sql"):
        caminho = BASE / "sql" / arquivo
        with conn.cursor() as cur:
            cur.execute(caminho.read_text(encoding="utf-8"))
        print(f"  aplicado {arquivo}")
    conn.commit()


def carregar(conn: psycopg.Connection, csv_nome: str, tabela: str) -> int:
    caminho = DADOS / csv_nome
    if not caminho.exists():
        raise FileNotFoundError(f"não encontrei {caminho}")

    with caminho.open(newline="", encoding="utf-8") as fh:
        leitor = csv.reader(fh)
        colunas = next(leitor)
        lista = ", ".join(f'"{c}"' for c in colunas)
        sql = f'COPY {SCHEMA}.{tabela} ({lista}) FROM STDIN'

        n = 0
        with conn.cursor() as cur, cur.copy(sql) as copy:
            for linha in leitor:
                copy.write_row([limpar(v, c) for v, c in zip(linha, colunas)])
                n += 1
    conn.commit()
    return n


def verificar(conn: psycopg.Connection) -> bool:
    """Confere contagens, integridade referencial e as ressalvas conhecidas."""
    esperado = {
        "pessoa": 1130, "periodo_observacao": 1126, "atendimento": 32153,
        "condicao": 7900, "exposicao_medicamento": 29518, "procedimento": 17333,
        "exame": 199514, "observacao": 8518, "periodo_condicao": 7897,
        "periodo_medicamento": 6652, "dicionario_conceitos": 535,
    }
    ok = True
    print("\n=== Contagem de linhas ===")
    with conn.cursor() as cur:
        for tabela, qtd in esperado.items():
            cur.execute(f"SELECT count(*) FROM {SCHEMA}.{tabela}")
            real = cur.fetchone()[0]
            marca = "OK" if real == qtd else "ERRO"
            if real != qtd:
                ok = False
            print(f"  {tabela:24} {real:>7} (esperado {qtd:>7})  {marca}")

        print("\n=== Integridade referencial ===")
        checks = [
            ("condicao sem pessoa",
             f"SELECT count(*) FROM {SCHEMA}.condicao c LEFT JOIN {SCHEMA}.pessoa p "
             f"ON p.id_pessoa=c.id_pessoa WHERE p.id_pessoa IS NULL"),
            ("exame sem pessoa",
             f"SELECT count(*) FROM {SCHEMA}.exame e LEFT JOIN {SCHEMA}.pessoa p "
             f"ON p.id_pessoa=e.id_pessoa WHERE p.id_pessoa IS NULL"),
            ("condicao com atendimento inexistente",
             f"SELECT count(*) FROM {SCHEMA}.condicao c LEFT JOIN {SCHEMA}.atendimento a "
             f"ON a.id_atendimento=c.id_atendimento "
             f"WHERE c.id_atendimento IS NOT NULL AND a.id_atendimento IS NULL"),
        ]
        for rotulo, sql in checks:
            cur.execute(sql)
            n = cur.fetchone()[0]
            if n:
                ok = False
            print(f"  {rotulo:40} {n}  {'OK' if n == 0 else 'ERRO'}")

        print("\n=== Ressalvas conhecidas do dataset ===")
        cur.execute(f"SELECT count(*) FROM {SCHEMA}.exame WHERE valor_numerico IS NOT NULL")
        print(f"  exames com valor numérico: {cur.fetchone()[0]} (esperado 0 — resultados "
              f"perdidos no ETL original)")
        cur.execute(f"SELECT count(*) FROM {SCHEMA}.exposicao_medicamento "
                    f"WHERE inconsistencia_vocabulario IS NOT NULL")
        print(f"  medicamentos com código de condição: {cur.fetchone()[0]} (esperado 7899)")
        cur.execute(f"SELECT count(*) FROM {SCHEMA}.vw_medicamento_valido")
        print(f"  medicamentos válidos (vw_medicamento_valido): {cur.fetchone()[0]}")
        cur.execute(f"SELECT count(*) FROM {SCHEMA}.pessoa") 
        total = cur.fetchone()[0]
        cur.execute(f"SELECT count(*) FROM {SCHEMA}.vw_pessoa_valida")
        print(f"  pacientes com nascimento plausível: {cur.fetchone()[0]} de {total}")
    return ok


def main() -> int:
    ap = argparse.ArgumentParser(description="Popula o Postgres com o dataset Synthea PT")
    ap.add_argument("--recriar", action="store_true",
                    help="dropa e recria o schema antes de carregar")
    ap.add_argument("--verificar", action="store_true",
                    help="apenas valida o conteúdo já carregado")
    args = ap.parse_args()

    if not DADOS.exists():
        return print(f"ERRO: {DADOS} não existe") or 1

    try:
        conn = conectar()
    except psycopg.OperationalError as e:
        print(f"ERRO ao conectar no Postgres: {e}")
        print("O container está de pé?   docker compose up -d")
        return 1

    with conn:
        if args.verificar:
            return 0 if verificar(conn) else 1

        if args.recriar:
            recriar_schema(conn)
        else:
            with conn.cursor() as cur:
                cur.execute("SELECT to_regclass(%s)", (f"{SCHEMA}.pessoa",))
                if cur.fetchone()[0] is None:
                    print("Schema ainda não existe — criando.")
                    recriar_schema(conn)

        # tabelas já populadas? evita duplicar por engano
        with conn.cursor() as cur:
            cur.execute(f"SELECT count(*) FROM {SCHEMA}.pessoa")
            if cur.fetchone()[0] > 0:
                print("O banco já contém dados. Use --recriar para recarregar do zero.")
                return 1

        print(f"Carregando de {DADOS}\n")
        inicio = time.perf_counter()
        total = 0
        for csv_nome, tabela in TABELAS:
            t0 = time.perf_counter()
            n = carregar(conn, csv_nome, tabela)
            total += n
            print(f"  {tabela:24} {n:>7} linhas  ({time.perf_counter() - t0:5.2f}s)")

        print(f"\n{total} linhas em {time.perf_counter() - inicio:.1f}s")

        with conn.cursor() as cur:
            cur.execute(f"ANALYZE")
        conn.commit()

        return 0 if verificar(conn) else 1


if __name__ == "__main__":
    sys.exit(main())
