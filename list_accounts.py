import os
import sys

# Adiciona o diretório atual ao path para resolver as importações
sys.path.append(os.getcwd())

from app import create_app, db
from app.models import ContaContabil, TipoConta

def list_accounts():
    app = create_app()
    with app.app_context():
        # Busca contas de despesa que podem ser juros ou encargos
        contas = db.session.query(ContaContabil).filter(
            ContaContabil.tipo == TipoConta.DESPESA.value
        ).all()
        for c in contas:
            if c.is_analitica():
                print(f"{c.id}: {c.nome}")

if __name__ == "__main__":
    list_accounts()
