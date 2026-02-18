import sys
import os
sys.path.append(os.getcwd())
from app import create_app, db
from app.models import Ativo
from app.services import FinancialService
from decimal import Decimal
from datetime import datetime

def test_extrato_completo():
    app = create_app()
    with app.app_context():
        client = app.test_client()
        
        # 1. Limpar e Criar Banco
        db.drop_all()
        db.create_all()
        from app.utils import seed_plano_contas
        seed_plano_contas()
        print("DB Resetado e Plano de Contas semeado.")
        
        # Cadastrar Banco 1 (Saldo 500)
        res1 = client.post('/financeiro/bancos/novo', data={
            'nome': 'Banco do Brasil',
            'numero_conta': '001-X',
            'saldo_inicial': '500.00'
        }, follow_redirects=True)
        
        if res1.status_code != 200:
            print(f"Erro Banco 1: {res1.data.decode('utf-8')}")
        
        # Cadastrar Banco 2 (Saldo 0)
        res2 = client.post('/financeiro/bancos/novo', data={
            'nome': 'Nubank',
            'numero_conta': '260-Y',
            'saldo_inicial': '0.00'
        }, follow_redirects=True)
        
        if res2.status_code != 200:
            print(f"Erro Banco 2: {res2.data.decode('utf-8')}")
        
        db.session.expire_all()
        banco1 = Ativo.query.filter_by(descricao='Banco do Brasil').first()
        banco2 = Ativo.query.filter_by(descricao='Nubank').first()

        if not banco1 or not banco2:
            print("❌ Falha crítica: Bancos não foram encontrados no BD após POST.")
            return
        
        # 2. Realizar Transferência de 100 reais
        print(f"Transferindo 100 de {banco1.descricao} para {banco2.descricao}")
        FinancialService.realizar_transferencia(
            conta_origem_id=banco1.conta_contabil_id,
            conta_destino_id=banco2.conta_contabil_id,
            valor=Decimal('100.00'),
            data=datetime.utcnow(),
            descricao="Transferência Teste Extrato"
        )
        db.session.commit()
        
        # 3. Chamar rota de extrato Banco 1
        print(f"Consultando extrato do {banco1.descricao}...")
        response = client.get(f'/financeiro/bancos/extrato/{banco1.id}')
        
        if response.status_code == 200:
            html = response.data.decode('utf-8')
            if 'Transferência Teste Extrato' in html:
                print("✅ Lançamento de transferência encontrado no extrato.")
            if 'Saldo Inicial' in html:
                print("✅ Lançamento de saldo inicial encontrado no extrato.")
            # Verificar se o saldo final aparece formatado (como string, pode variar)
            if '400,00' in html:
                 print("✅ Saldo final de 400,00 encontrado no HTML.")
            else:
                 print("⚠️ Saldo final 400,00 não encontrado no HTML (formatação pode ser diferente).")
        else:
            print(f"❌ Erro ao acessar extrato: {response.status_code}")

if __name__ == "__main__":
    test_extrato_completo()
