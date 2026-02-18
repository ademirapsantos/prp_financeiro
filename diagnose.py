from app import create_app, db
from app.models import Ativo, LivroDiario, PartidaDiario, TransacaoFinanceira, ContaContabil, Titulo
from decimal import Decimal

app = create_app()
with app.app_context():
    print('--- SALDOS DOS ATIVOS ---')
    ativos = Ativo.query.all()
    for b in ativos:
        print(f'Ativo: {b.descricao} (ID: {b.id}, Tipo: {b.tipo}), Saldo: {b.valor_atual}, Conta: {b.conta_contabil.codigo if b.conta_contabil else "N/A"}')
    
    print('\n--- SALDO CONTABILL (1.1.01) ---')
    contas_disp = ContaContabil.query.filter(ContaContabil.codigo.like('1.1.01%')).all()
    for c in contas_disp:
        debitos = db.session.query(db.func.sum(PartidaDiario.valor)).filter(PartidaDiario.conta_id == c.id, PartidaDiario.tipo == 'D').scalar() or Decimal('0')
        creditos = db.session.query(db.func.sum(PartidaDiario.valor)).filter(PartidaDiario.conta_id == c.id, PartidaDiario.tipo == 'C').scalar() or Decimal('0')
        print(f'Conta: {c.nome} ({c.codigo}), D: {debitos}, C: {creditos}, Saldo: {debitos - creditos}')

    print('\n--- TITULOS ---')
    titulos = Titulo.query.order_by(Titulo.id.desc()).limit(10).all()
    for t in titulos:
        print(f'ID: {t.id}, Desc: {t.descricao}, Valor: {t.valor}, Tipo: {t.tipo}, Status: {t.status}')

    print('\n--- ULTIMOS LANCAMENTOS NO DIARIO ---')
    diarios = LivroDiario.query.order_by(LivroDiario.id.desc()).limit(30).all()
    for d in diarios:
        print(f'\nID: {d.id}, Data: {d.data}, Hist: {d.historico}')
        for p in d.partidas:
            print(f'  - {p.tipo} | {p.conta.codigo} {p.conta.nome} | {p.valor}')
