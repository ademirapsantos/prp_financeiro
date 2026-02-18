from app import create_app, db
from app.models import Titulo, Ativo

app = create_app()
with app.app_context():
    titles = Titulo.query.all()
    actives = Ativo.query.all()
    
    print(f"Total de Ativos: {len(actives)}")
    for a in actives:
        print(f"AT-ID: {a.id}, Desc: {a.descricao}")
        
    print(f"\nTotal de Titulos: {len(titles)}")
    for t in titles:
        print(f"T-ID: {t.id}, Desc: {t.descricao}, AtivoID: {t.ativo_id}")
