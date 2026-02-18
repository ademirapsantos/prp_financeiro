from app import create_app, db
from app.models import Entidade, ContaContabil

app = create_app()
with app.app_context():
    print("--- ENTIDADES ---")
    entidades = Entidade.query.all()
    for e in entidades:
        conta = db.session.get(ContaContabil, e.conta_contabil_id) if e.conta_contabil_id else None
        conta_nome = f"{conta.codigo} - {conta.nome} ({conta.tipo})" if conta else "Nenhuma"
        print(f"ID: {e.id} | Nome: {e.nome} | Conta: {conta_nome}")
    
    print("\n--- CONTAS DE PATRIMÔNIO LÍQUIDO ---")
    contas_pl = ContaContabil.query.filter(ContaContabil.tipo == 'Patrimônio Líquido').all()
    for c in contas_pl:
        print(f"Código: {c.codigo} | Nome: {c.nome}")
