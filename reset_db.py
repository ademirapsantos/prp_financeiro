import os
import time

# Usar caminho absoluto para garantir que deletamos o arquivo certo
basedir = os.path.abspath(os.path.dirname(__file__))
db_file = os.path.join(basedir, 'data/prp_financeiro.db')

if os.path.exists(db_file):
    try:
        os.remove(db_file)
        print(f"Arquivo {db_file} removido com sucesso.")
    except PermissionError:
        print(f"Erro de permissão ao remover {db_file}. Tentando novamente em 2 segundos...")
        time.sleep(2)
        try:
            os.remove(db_file)
            print(f"Arquivo {db_file} removido com sucesso na segunda tentativa.")
        except Exception as e:
            print(f"Falha ao remover {db_file}: {e}")
else:
    print(f"Arquivo {db_file} não existe.")

# Recriar tabelas
from app import create_app, db
app = create_app()
with app.app_context():
    db.create_all()
    print("Tabelas recriadas com sucesso.")
