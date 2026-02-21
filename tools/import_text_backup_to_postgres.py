#!/usr/bin/env python3
"""
Importa backup textual por seções para PostgreSQL.

Formato esperado:
--- TABLE: nome_tabela ---
col1,col2,...
v1,v2,...

Uso:
  python tools/import_text_backup_to_postgres.py ^
    --input "D:\\...\\backup_uuid.txt" ^
    --database-url "postgresql://user:pass@localhost:5433/prp_financeiro"
"""

from __future__ import annotations

import argparse
import csv
import io
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

import psycopg
from psycopg import sql


@dataclass
class TableSection:
    name: str
    columns: List[str]
    rows: List[List[str]]


# Ordem segura de carga considerando dependências.
IMPORT_ORDER = [
    "users",
    "contas_contabeis",
    "entidades",
    "ativos",
    "titulos",
    "transacoes_financeiras",
    "livro_diario",
    "partidas_diario",
    "configuracoes",
    "configuracao_smtp",
    "cartoes_credito",
    "faturas_cartao",
    "transacoes_cartao",
    "pagamentos_fatura_cartao",
    "update_logs",
    "notificacoes",
]


def read_text_best_effort(path: Path) -> str:
    for enc in ("utf-8", "utf-8-sig", "cp1252", "latin-1"):
        try:
            return path.read_text(encoding=enc)
        except UnicodeDecodeError:
            continue
    return path.read_text(encoding="utf-8", errors="replace")


def parse_sections(text: str) -> List[TableSection]:
    sections: List[TableSection] = []
    current_name = None
    current_lines: List[str] = []

    def flush() -> None:
        nonlocal current_name, current_lines
        if not current_name:
            return
        payload = [ln for ln in current_lines if ln.strip()]
        if not payload:
            sections.append(TableSection(current_name, [], []))
        else:
            reader = csv.reader(io.StringIO("\n".join(payload)))
            rows = list(reader)
            columns = rows[0] if rows else []
            data_rows = rows[1:] if len(rows) > 1 else []
            sections.append(TableSection(current_name, columns, data_rows))
        current_name = None
        current_lines = []

    for raw in text.splitlines():
        line = raw.rstrip("\n")
        stripped = line.strip()
        if stripped.startswith("--- TABLE: ") and stripped.endswith(" ---"):
            flush()
            current_name = stripped[len("--- TABLE: ") : -len(" ---")].strip()
            continue
        if current_name:
            current_lines.append(line)

    flush()
    return sections


def sort_sections(sections: List[TableSection]) -> List[TableSection]:
    by_name: Dict[str, TableSection] = {s.name: s for s in sections}
    ordered: List[TableSection] = []

    for t in IMPORT_ORDER:
        if t in by_name:
            ordered.append(by_name.pop(t))

    # Qualquer tabela não mapeada vai por último.
    for _, sec in sorted(by_name.items(), key=lambda x: x[0]):
        ordered.append(sec)
    return ordered


def normalize_row(row: List[str], expected_len: int) -> List[object]:
    out = row[:expected_len] + [""] * max(0, expected_len - len(row))
    return [None if v == "" else v for v in out]


def import_sections(database_url: str, sections: List[TableSection]) -> None:
    sections = [s for s in sections if s.columns]
    if not sections:
        raise RuntimeError("Nenhuma seção de tabela válida encontrada no arquivo.")

    table_names = [s.name for s in sections]

    with psycopg.connect(database_url, autocommit=False) as conn:
        with conn.cursor() as cur:
            # Limpa dados mantendo estrutura.
            truncate_stmt = sql.SQL("TRUNCATE TABLE {} CASCADE").format(
                sql.SQL(", ").join(sql.Identifier(t) for t in table_names)
            )
            cur.execute(truncate_stmt)

            for sec in sections:
                cols = sec.columns
                if not cols:
                    continue

                insert_stmt = sql.SQL("INSERT INTO {} ({}) VALUES ({})").format(
                    sql.Identifier(sec.name),
                    sql.SQL(", ").join(sql.Identifier(c) for c in cols),
                    sql.SQL(", ").join(sql.Placeholder() for _ in cols),
                )

                payload = [normalize_row(r, len(cols)) for r in sec.rows]
                if payload:
                    cur.executemany(insert_stmt, payload)

        conn.commit()


def main() -> int:
    parser = argparse.ArgumentParser(description="Importa backup textual para PostgreSQL.")
    parser.add_argument("--input", required=True, help="Arquivo de backup textual (TABLE sections).")
    parser.add_argument(
        "--database-url",
        default=os.getenv("DATABASE_URL", ""),
        help="URL do PostgreSQL. Se omitido, usa env DATABASE_URL.",
    )
    args = parser.parse_args()

    if not args.database_url:
        raise RuntimeError("Informe --database-url ou defina DATABASE_URL no ambiente.")

    in_path = Path(args.input)
    if not in_path.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {in_path}")

    text = read_text_best_effort(in_path)
    sections = sort_sections(parse_sections(text))
    import_sections(args.database_url, sections)

    print(f"Importação concluída com sucesso: {in_path}")
    print(f"Tabelas importadas: {len([s for s in sections if s.columns])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

