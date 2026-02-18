import sys
import os
sys.path.append(os.getcwd())
from app import create_app, db
from app.models import ContaContabil

app = create_app()
with app.app_context():
    contas = ContaContabil.query.all()
    for c in contas:
        print(f"{c.codigo} | {c.nome} | {c.tipo}")
