import sqlite3
import os

db_path = 'data/prp_financeiro.db'
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM faturas_cartao WHERE competencia = '2026-03'")
    rows = cursor.fetchall()
    for r in rows:
        d = dict(r)
        print(f"ID: {d['id']}, Comp: {d['competencia']}, Status: {d['status']}, Pagto: {d['situacao_pagamento']}, Total: {d['total']}, Pago: {d['total_pago']}")
        
    conn.close()
else:
    print("Banco de dados não encontrado.")
