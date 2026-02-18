from app import create_app, db
from app.models import Ativo, ContaContabil
from app.services import FinancialService
from decimal import Decimal
import datetime

def test_financeiro_flow():
    app = create_app()
    app.config['PROPAGATE_EXCEPTIONS'] = True
    
    with app.app_context():
        print("--- 1. Preparando Massa de Dados (Cenário de Transferência) ---")
        # Precisamos de 2 contas bancárias (ativos)
        # Vamos assumir que o seed já criou algumas ou vamos criar.
        
        # Consultar Bancos
        conta_itau = ContaContabil.query.filter(ContaContabil.nome.like('%Itaú%')).first()
        conta_nubank = ContaContabil.query.filter(ContaContabil.nome.like('%NuBank%')).first()
        if not conta_itau:
             print("❌ Conta Itaú não encontrada.")
             # Tentar achar genérica
             conta_itau = ContaContabil.query.filter(ContaContabil.codigo == '1.1.01.001').first()
        if not conta_nubank:
             print("❌ Conta NuBank não encontrada.")
             # Tentar achar outra genérica
             conta_nubank = ContaContabil.query.filter(ContaContabil.codigo == '1.1.01.002').first()
             
        if not conta_itau or not conta_nubank:
            print("❌ Não foi possível encontrar duas contas para transferir.")
            return

        print(f"Origem: {conta_itau.nome} (ID: {conta_itau.id})")
        print(f"Destino: {conta_nubank.nome} (ID: {conta_nubank.id})")

        print("--- 2. Executando Transferência ---")
        try:
            FinancialService.realizar_transferencia(
                conta_origem_id=conta_itau.id,
                conta_destino_id=conta_nubank.id,
                valor=Decimal('500.00'),
                data=datetime.date.today(),
                descricao="Transf. Teste Unitário"
            )
            db.session.commit()
            print("✅ Transferência executada com sucesso.")
        except Exception as e:
            print(f"❌ Erro na Transferência: {e}")
            return

        print("--- 3. Verificações ---")
        # Verificar se Transacao foi criada
        from app.models import TransacaoFinanceira, TipoTransacao
        transacao = TransacaoFinanceira.query.filter_by(tipo=TipoTransacao.TRANSFERENCIA.value, valor=500.00).first()
        if transacao:
             print(f"✅ Transação Financeira Criada: ID {transacao.id}")
        else:
             print("❌ Transação não encontrada.")
             
        # Verificar Lançamento Contábil
        # Deve ter um Débito na conta destino e Crédito na conta origem
        # Vamos checar via query nas partidas da transação (se vinculado) ou pelo histórico
        # Como o service vincula:
        if transacao and transacao.lancamentos_contabeis: # É uma lista ? Backref retorna lista?
            # lancamentos_contabeis backref='transacao_origem' in LivroDiario
            diario = transacao.lancamentos_contabeis[0] # Lista de diarios
            print(f"✅ Diário Contábil Vinculado: ID {diario.id}")
            
            partidas = diario.partidas
            debito = next((p for p in partidas if p.tipo == 'D'), None)
            credito = next((p for p in partidas if p.tipo == 'C'), None)
            
            if debito and debito.conta_id == conta_nubank.id and debito.valor == 500.00:
                print("✅ Débito no Destino (NuBank) OK")
            else:
                print(f"❌ Erro no Débito: {debito}")
                
            if credito and credito.conta_id == conta_itau.id and credito.valor == 500.00:
                print("✅ Crédito na Origem (Itaú) OK")
            else:
                print(f"❌ Erro no Crédito: {credito}")
        else:
            print("⚠️ Sem vínculo direto ou backref falhou. Checando Diário isoladamente...")

if __name__ == "__main__":
    test_financeiro_flow()
