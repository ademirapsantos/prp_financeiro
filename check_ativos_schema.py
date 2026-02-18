import sqlite3
import os

db_path = os.path.join(os.getcwd(), 'prp_financeiro.db')

def check_schema():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(ativos)")
    columns = cursor.fetchall()
    print("Colunas na tabela 'ativos':")
    for col in columns:
        print(f"ID: {col[0]}, Nome: {col[1]}, Tipo: {col[2]}")
    conn.close()

if __name__ == "__main__":
    check_schema()
