import sqlite3
import os

db_path = 'data/prp_financeiro.db'
if not os.path.exists(db_path):
    print(f"Erro: Banco não encontrado em {os.path.abspath(db_path)}")
    exit(1)

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("ALTER TABLE users ADD COLUMN tema TEXT DEFAULT 'light';")
    conn.commit()
    conn.close()
    print("Coluna 'tema' adicionada com sucesso à tabela 'users'!")
except sqlite3.OperationalError as e:
    if "duplicate column name" in str(e):
        print("A coluna 'tema' já existe.")
    else:
        print(f"Erro SQLite: {e}")
except Exception as e:
    print(f"Erro inesperado: {e}")
