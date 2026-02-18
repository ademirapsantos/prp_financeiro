from app import create_app, db
from app.models import ContaContabil, PartidaDiario, LivroDiario
import csv

app = create_app()
with app.app_context():
    itau = ContaContabil.query.filter(ContaContabil.nome.like("%Itaú%")).first()
    partidas = PartidaDiario.query.filter_by(conta_id=itau.id).all()
    
    with open('itau_audit.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['ID_Partida', 'ID_Diario', 'Data', 'Tipo', 'Valor', 'Historico', 'Transacao_ID'])
        for p in partidas:
            d = p.diario
            writer.writerow([p.id, d.id, d.data, p.tipo, p.valor, d.historico, d.transacao_id])
            
    print("Relatório itau_audit.csv gerado com sucesso.")
