from app import create_app, db
from app.models import Ativo, ContaContabil, PartidaDiario
from decimal import Decimal
from datetime import datetime

def test_ajuste_saldo():
    app = create_app()
    with app.app_context():
        client = app.test_client()
        
        # 1. Cadastrar um banco com 100.00
        print("--- 1. Cadastrando Banco Inicial ---")
        client.post('/financeiro/bancos/novo', data={
            'nome': 'Banco de Ajuste',
            'numero_conta': '123-X',
            'saldo_inicial': '100.00'
        })
        
        banco = Ativo.query.filter_by(descricao='Banco de Ajuste').first()
        print(f"Banco criado ID: {banco.id}, Número: {banco.numero_conta}")

        # 2. Ajustar para 150.00 (Diferença +50.00)
        print("\n--- 2. Ajustando Saldo para 150.00 (+50.00) ---")
        client.post(f'/financeiro/bancos/editar/{banco.id}', data={
            'nome': 'Banco de Ajuste',
            'numero_conta': '123-X-NOVO',
            'valor': '150.00'
        })
        
        db.session.refresh(banco)
        # Calcular saldo real via partidas
        stmt = db.session.query(
            db.func.sum(PartidaDiario.valor).filter(PartidaDiario.tipo == 'D').label('debitos'),
            db.func.sum(PartidaDiario.valor).filter(PartidaDiario.tipo == 'C').label('creditos')
        ).filter(PartidaDiario.conta_id == banco.conta_contabil_id)
        res = stmt.first()
        saldo_real = (res.debitos or 0) - (res.creditos or 0)
        
        print(f"Novo Número da Conta: {banco.numero_conta}")
        print(f"Saldo Contábil Real: {saldo_real}")
        
        if saldo_real == Decimal('150.00'):
            print("✅ Saldo Ajustado com sucesso (Lançamento contábil gerado)")
        else:
            print(f"❌ Falha no ajuste. Saldo esperado 150.00, real {saldo_real}")

if __name__ == "__main__":
    test_ajuste_saldo()
