import sqlite3
import os

def migrate():
    basedir = os.path.abspath(os.path.dirname(__file__))
    db_path = os.path.join(basedir, 'data/prp_financeiro.db')
    
    if not os.path.exists(db_path):
        print(f"Banco de dados não encontrado em: {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    columns = [
        ("valor_bruto", "NUMERIC(10, 2)"),
        ("valor_desconto", "NUMERIC(10, 2) DEFAULT 0.0"),
        ("valor_liquido", "NUMERIC(10, 2) DEFAULT 0.0")
    ]

    for col_name, col_type in columns:
        try:
            print(f"Adicionando coluna '{col_name}' à tabela 'transacoes_financeiras'...")
            cursor.execute(f"ALTER TABLE transacoes_financeiras ADD COLUMN {col_name} {col_type}")
            conn.commit()
            print(f"Coluna '{col_name}' adicionada com sucesso!")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e).lower():
                print(f"A coluna '{col_name}' já existe.")
            else:
                print(f"Erro ao adicionar coluna '{col_name}': {e}")
    
    conn.close()

if __name__ == "__main__":
    migrate()
