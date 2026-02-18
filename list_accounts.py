from app import app, db
from app.models import ContaContabil

with app.app_context():
    contas = ContaContabil.query.all()
    print("ID | Código | Nome | Tipo")
    print("-" * 30)
    for c in contas:
        print(f"{c.id} | {c.codigo} | {c.nome} | {c.tipo}")
