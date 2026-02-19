import sqlite3
import os

def migrate():
    basedir = os.path.abspath(os.path.dirname(__file__))
    db_path = os.path.join(basedir, 'prp_financeiro.db')
    
    if not os.path.exists(db_path):
        print(f"Banco de dados não encontrado em: {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        print("Adicionando coluna 'parcela_atual' à tabela 'titulos'...")
        cursor.execute("ALTER TABLE titulos ADD COLUMN parcela_atual INTEGER")
        conn.commit()
        print("Coluna adicionada com sucesso!")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e).lower():
            print("A coluna 'parcela_atual' já existe.")
        else:
            print(f"Erro ao adicionar coluna: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
