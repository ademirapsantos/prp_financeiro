from app import create_app, db
from app.models import ContaContabil, Entidade, Ativo

app = create_app()

with app.app_context():
    contas = ContaContabil.query.count()
    entidades = Entidade.query.count()
    ativos = Ativo.query.count()
    
    print(f"Contas Contábeis: {contas}")
    print(f"Entidades: {entidades}")
    print(f"Ativos: {ativos}")

    if contas > 0:
        print("✅ Banco de dados inicializado e populado com sucesso.")
    else:
        print("❌ Falha na população do banco de dados.")
