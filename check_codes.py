from app import create_app
from app.models import ContaContabil

app = create_app()
with app.app_context():
    codes = ['1.1.05', '1.5', '2.3']
    for code in codes:
        c = ContaContabil.query.filter(ContaContabil.codigo.like(f'{code}%')).first()
        if c:
            print(f"{code}: {c.nome}")
        else:
            print(f"{code}: NOT FOUND")
