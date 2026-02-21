#!/usr/bin/env python3
import argparse
from typing import Dict, List

from sqlalchemy import MetaData, create_engine, func, select, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError


def get_engines(sqlite_path: str, postgres_url: str) -> tuple[Engine, Engine]:
    src = create_engine(f"sqlite:///{sqlite_path}")
    pg_url = postgres_url
    if pg_url.startswith("postgres://"):
        pg_url = pg_url.replace("postgres://", "postgresql+psycopg://", 1)
    elif pg_url.startswith("postgresql://") and "+psycopg" not in pg_url:
        pg_url = pg_url.replace("postgresql://", "postgresql+psycopg://", 1)
    dst = create_engine(pg_url)
    return src, dst


def reflect_metadata(engine: Engine) -> MetaData:
    metadata = MetaData()
    metadata.reflect(bind=engine)
    return metadata


def truncate_target(dst_engine: Engine, dst_meta: MetaData) -> None:
    table_names = [t.name for t in dst_meta.sorted_tables]
    if not table_names:
        return
    with dst_engine.begin() as conn:
        joined = ", ".join([f'"{name}"' for name in table_names])
        conn.execute(text(f"TRUNCATE TABLE {joined} RESTART IDENTITY CASCADE"))


def copy_tables(src_engine: Engine, dst_engine: Engine, batch_size: int = 1000) -> Dict[str, int]:
    src_meta = reflect_metadata(src_engine)
    dst_meta = reflect_metadata(dst_engine)

    copied: Dict[str, int] = {}
    with src_engine.connect() as src_conn, dst_engine.begin() as dst_conn:
        for src_table in src_meta.sorted_tables:
            dst_table = dst_meta.tables.get(src_table.name)
            if not dst_table:
                continue

            src_cols = list(src_table.c.keys())
            dst_cols = set(dst_table.c.keys())
            common_cols = [c for c in src_cols if c in dst_cols]
            if not common_cols:
                copied[src_table.name] = 0
                continue

            total = src_conn.execute(
                select(func.count()).select_from(src_table)
            ).scalar_one()
            copied[src_table.name] = int(total)
            if total == 0:
                continue

            offset = 0
            while offset < total:
                rows = src_conn.execute(
                    select(*[src_table.c[c] for c in common_cols]).limit(batch_size).offset(offset)
                ).mappings().all()
                if not rows:
                    break
                payload: List[dict] = [dict(r) for r in rows]
                dst_conn.execute(dst_table.insert(), payload)
                offset += len(payload)

    return copied


def sync_sequences(dst_engine: Engine, dst_meta: MetaData) -> None:
    with dst_engine.begin() as conn:
        for table in dst_meta.sorted_tables:
            pk_cols = list(table.primary_key.columns)
            if len(pk_cols) != 1:
                continue
            col = pk_cols[0]
            try:
                is_int = col.type.python_type is int
            except Exception:
                is_int = False
            if not is_int:
                continue

            sql = text(
                f"""
                SELECT setval(
                    pg_get_serial_sequence(:table_name, :col_name),
                    COALESCE((SELECT MAX("{col.name}") FROM "{table.name}"), 1),
                    true
                )
                """
            )
            conn.execute(sql, {"table_name": table.name, "col_name": col.name})


def main() -> int:
    parser = argparse.ArgumentParser(description="Migra dados de SQLite para Postgres.")
    parser.add_argument("--sqlite-path", required=True, help="Caminho do arquivo SQLite (.db)")
    parser.add_argument("--postgres-url", required=True, help="URL do Postgres")
    parser.add_argument("--batch-size", type=int, default=1000, help="Tamanho do lote de cópia")
    parser.add_argument(
        "--truncate-target",
        action="store_true",
        help="Limpa tabelas de destino antes da cópia (TRUNCATE CASCADE)",
    )
    args = parser.parse_args()

    try:
        src_engine, dst_engine = get_engines(args.sqlite_path, args.postgres_url)
        dst_meta = reflect_metadata(dst_engine)
        if args.truncate_target:
            truncate_target(dst_engine, dst_meta)

        copied = copy_tables(src_engine, dst_engine, batch_size=args.batch_size)
        sync_sequences(dst_engine, reflect_metadata(dst_engine))

        print("Migracao concluida.")
        for table_name, count in copied.items():
            print(f"- {table_name}: {count} registros")
        return 0
    except SQLAlchemyError as exc:
        print(f"Erro SQLAlchemy: {exc}")
        return 1
    except Exception as exc:
        print(f"Erro: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
