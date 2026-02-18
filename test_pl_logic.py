from app import create_app, db
from app.models import ContaContabil, TipoConta, PartidaDiario, LivroDiario
from decimal import Decimal
from sqlalchemy import func

def get_pl():
    def get_saldo(tipo):
        if tipo == TipoConta.ATIVO.value:
            exclude = ['1.1.05']
        else:
            exclude = []
        
        stmt = db.session.query(
            func.sum(PartidaDiario.valor).filter(PartidaDiario.tipo == 'D').label('debitos'),
            func.sum(PartidaDiario.valor).filter(PartidaDiario.tipo == 'C').label('creditos')
        ).join(ContaContabil).filter(ContaContabil.tipo == tipo)
        
        for prefix in exclude:
            stmt = stmt.filter(~ContaContabil.codigo.like(f'{prefix}%'))
            
        res = stmt.first()
        deb = res.debitos or 0
        cre = res.creditos or 0
        return (deb - cre) if tipo == TipoConta.ATIVO.value else (cre - deb)

    ativo = get_saldo(TipoConta.ATIVO.value)
    passivo = get_saldo(TipoConta.PASSIVO.value)
    return ativo - passivo

app = create_app()
with app.app_context():
    print(f"PL ANTES: R$ {get_pl():.2f}")
    
    # Criar um teste temporário (Fornecedores 2.3)
    conta_forn = ContaContabil.query.filter(ContaContabil.codigo.like('2.3%')).first()
    conta_banco = ContaContabil.query.filter(ContaContabil.codigo.like('1.1.01%')).first()
    
    if conta_forn and conta_banco:
        print(f"Testando com conta {conta_forn.codigo} ({conta_forn.nome})")
        diario = LivroDiario(historico="TESTE PL")
        db.session.add(diario)
        db.session.flush()
        
        # Simular uma dívida de 1000 reais
        # D: Despesa (não afeta o PL aqui pois focamos no Balanço 1 vs 2)
        # C: Passivo (+1000)
        p1 = PartidaDiario(diario_id=diario.id, conta_id=conta_forn.id, tipo='C', valor=Decimal('1000.00'))
        db.session.add(p1)
        db.session.commit()
        
        print(f"PL APÓS DIVIDA DE 1000: R$ {get_pl():.2f}")
        
        # Liquidar a dívida
        # D: Passivo (-1000) -> Zera o passivo
        # C: Ativo/Banco (-1000) -> Diminui o ativo
        diario2 = LivroDiario(historico="LIQUIDACAO TESTE")
        db.session.add(diario2)
        db.session.flush()
        
        p2 = PartidaDiario(diario_id=diario2.id, conta_id=conta_forn.id, tipo='D', valor=Decimal('1000.00'))
        p3 = PartidaDiario(diario_id=diario2.id, conta_id=conta_banco.id, tipo='C', valor=Decimal('1000.00'))
        db.session.add(p2)
        db.session.add(p3)
        db.session.commit()
        
        print(f"PL APÓS PAGAMENTO: R$ {get_pl():.2f}")
        
        # Cleanup
        db.session.delete(p1)
        db.session.delete(p2)
        db.session.delete(p3)
        db.session.delete(diario)
        db.session.delete(diario2)
        db.session.commit()
        print("Cleanup concluído.")
    else:
        print("Contas para teste não encontradas.")
