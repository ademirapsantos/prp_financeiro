import sqlite3
import os

db_path = os.path.join(os.getcwd(), 'data/prp_financeiro.db')

def update_schema():
    print(f"Conectando ao banco de dados: {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Lista de colunas para adicionar
    columns_to_add = [
        ("quantidade", "FLOAT DEFAULT 0.0"),
        ("valor_unitario", "NUMERIC(10, 2) DEFAULT 0.0")
    ]
    
    for col_name, col_type in columns_to_add:
        try:
            print(f"Tentando adicionar coluna '{col_name}'...")
            cursor.execute(f"ALTER TABLE ativos ADD COLUMN {col_name} {col_type}")
            print(f"Coluna '{col_name}' adicionada com sucesso.")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e).lower():
                print(f"A coluna '{col_name}' já existe.")
            else:
                print(f"Erro ao adicionar coluna '{col_name}': {e}")
                
    conn.commit()
    conn.close()
    print("Atualização concluída.")

if __name__ == "__main__":
    update_schema()
