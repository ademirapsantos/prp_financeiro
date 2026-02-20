import sqlite3
import os
from datetime import date

db_path = 'prp_financeiro.db'
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    hoje = date.today().isoformat()
    print(f"Data de referência (Hoje): {hoje}")
    
    # Buscar faturas que estão 'fechada' mas a data de fechamento é futura
    cursor.execute("SELECT id, competencia, status, data_fechamento FROM faturas_cartao WHERE status = 'fechada' AND data_fechamento >= ?", (hoje,))
    faturas_para_corrigir = cursor.fetchall()
    
    if not faturas_para_corrigir:
        print("Nenhuma fatura com status incorreto encontrada.")
    else:
        for f in faturas_para_corrigir:
            print(f"Corrigindo fatura {f['competencia']} (ID: {f['id']}): 'fechada' -> 'aberta' (Fecha em: {f['data_fechamento']})")
            cursor.execute("UPDATE faturas_cartao SET status = 'aberta' WHERE id = ?", (f['id'],))
        
        conn.commit()
        print(f"{len(faturas_para_corrigir)} fatura(s) corrigida(s).")
        
    conn.close()
else:
    print("Banco de dados não encontrado.")
