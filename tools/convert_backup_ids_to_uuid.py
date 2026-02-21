#!/usr/bin/env python3
"""
Converte IDs inteiros para UUID em backup textual por seções:

--- TABLE: nome_tabela ---
col1,col2,...
v1,v2,...

Uso:
  python tools/convert_backup_ids_to_uuid.py --input backup.txt --output backup_uuid.txt
"""

from __future__ import annotations

import argparse
import csv
import io
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple


@dataclass
class TableSection:
    name: str
    columns: List[str]
    rows: List[List[str]]


FK_RULES: Dict[str, Dict[str, str]] = {
    "contas_contabeis": {"parent_id": "contas_contabeis"},
    "entidades": {
        "conta_contabil_id": "contas_contabeis",
        "conta_resultado_id": "contas_contabeis",
        "conta_venda_id": "contas_contabeis",
        "conta_compra_id": "contas_contabeis",
    },
    "ativos": {"conta_contabil_id": "contas_contabeis"},
    "titulos": {"entidade_id": "entidades", "ativo_id": "ativos"},
    "transacoes_financeiras": {"titulo_id": "titulos", "ativo_id": "ativos"},
    "livro_diario": {"transacao_id": "transacoes_financeiras"},
    "partidas_diario": {"diario_id": "livro_diario", "conta_id": "contas_contabeis"},
}

CONFIG_ACCOUNT_KEYS = {
    "conta_lucro_venda",
    "conta_prejuizo_venda",
    "conta_ativo_banco",
    "conta_ativo_veiculo",
    "conta_ativo_imovel",
    "conta_ativo_investimento",
    "conta_ativo_outros",
    "CONTA_DESCONTO_OBTIDO_ID",
    "CONTA_DESCONTO_CONCEDIDO_ID",
}


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
        if line.strip().startswith("--- TABLE: ") and line.strip().endswith(" ---"):
            flush()
            current_name = line.strip()[len("--- TABLE: ") : -len(" ---")].strip()
            continue
        if current_name:
            current_lines.append(line)

    flush()
    return sections


def is_int_id(value: str) -> bool:
    v = (value or "").strip()
    return v.isdigit()


def uuid_for(table: str, old_id: str, ns: uuid.UUID) -> str:
    return str(uuid.uuid5(ns, f"{table}:{old_id}"))


def build_id_maps(sections: List[TableSection], ns: uuid.UUID) -> Dict[Tuple[str, str], str]:
    id_map: Dict[Tuple[str, str], str] = {}
    for sec in sections:
        if "id" not in sec.columns:
            continue
        id_idx = sec.columns.index("id")
        for row in sec.rows:
            if id_idx >= len(row):
                continue
            old_id = row[id_idx].strip()
            if not old_id or not is_int_id(old_id):
                continue
            key = (sec.name, old_id)
            id_map[key] = uuid_for(sec.name, old_id, ns)
    return id_map


def replace_value(
    table: str,
    referenced_table: str,
    value: str,
    id_map: Dict[Tuple[str, str], str],
) -> str:
    v = (value or "").strip()
    if not v:
        return value
    new_v = id_map.get((referenced_table, v))
    return new_v if new_v else value


def transform_sections(sections: List[TableSection], ns: uuid.UUID) -> List[TableSection]:
    id_map = build_id_maps(sections, ns)
    out: List[TableSection] = []

    for sec in sections:
        cols = sec.columns[:]
        rows = [r[:] for r in sec.rows]
        col_index = {c: i for i, c in enumerate(cols)}

        # 1) PK id
        if "id" in col_index:
            i = col_index["id"]
            for r in rows:
                if i < len(r):
                    old_id = (r[i] or "").strip()
                    if old_id:
                        r[i] = id_map.get((sec.name, old_id), r[i])

        # 2) FKs por regra
        table_rules = FK_RULES.get(sec.name, {})
        for fk_col, ref_table in table_rules.items():
            if fk_col not in col_index:
                continue
            i = col_index[fk_col]
            for r in rows:
                if i < len(r):
                    r[i] = replace_value(sec.name, ref_table, r[i], id_map)

        # 3) Regra especial configuracoes.valor apontando para contas_contabeis
        if sec.name == "configuracoes" and "chave" in col_index and "valor" in col_index:
            i_key = col_index["chave"]
            i_val = col_index["valor"]
            for r in rows:
                if i_key < len(r) and i_val < len(r):
                    if r[i_key] in CONFIG_ACCOUNT_KEYS:
                        r[i_val] = replace_value(sec.name, "contas_contabeis", r[i_val], id_map)

        out.append(TableSection(sec.name, cols, rows))

    return out


def render_sections(sections: List[TableSection]) -> str:
    parts: List[str] = []
    for idx, sec in enumerate(sections):
        parts.append(f"--- TABLE: {sec.name} ---")
        if sec.columns:
            buf = io.StringIO()
            writer = csv.writer(buf, lineterminator="\n")
            writer.writerow(sec.columns)
            for r in sec.rows:
                writer.writerow(r)
            parts.append(buf.getvalue().rstrip("\n"))
        if idx < len(sections) - 1:
            parts.append("")
    return "\n".join(parts).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Converte IDs int para UUID em backup por seções.")
    parser.add_argument("--input", required=True, help="Arquivo de entrada (texto com seções TABLE)")
    parser.add_argument("--output", required=True, help="Arquivo de saída convertido")
    parser.add_argument(
        "--namespace",
        default="2ce89f66-7b7f-4f3e-bcc7-2bca7f0a4e3e",
        help="UUID namespace para geração determinística (default fixo do projeto)",
    )
    args = parser.parse_args()

    in_path = Path(args.input)
    out_path = Path(args.output)

    text = in_path.read_text(encoding="utf-8")
    sections = parse_sections(text)
    ns = uuid.UUID(args.namespace)
    transformed = transform_sections(sections, ns)
    output = render_sections(transformed)
    out_path.write_text(output, encoding="utf-8")

    print(f"Arquivo convertido gerado em: {out_path}")
    print(f"Tabelas processadas: {len(sections)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

