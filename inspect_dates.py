import sqlite3
import os

db_path = 'data/prp_financeiro.db'
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, competencia, status, situacao_pagamento, data_fechamento, data_vencimento FROM faturas_cartao WHERE competencia = '2026-03'")
    rows = cursor.fetchall()
    for r in rows:
        print(dict(r))
        
    conn.close()
else:
    print("Banco de dados não encontrado.")
