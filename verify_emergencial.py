
import os
import sys
from decimal import Decimal

# Adicionar o diretório atual ao path para importar o app
sys.path.append(os.getcwd())

from app import create_app, db
from app.models import CartaoCredito, FaturaCartao, PagamentoFaturaCartao, Ativo, TipoAtivo
from app.services import CreditCardService

app = create_app()

def test_emergency_limit():
    with app.app_context():
        # 1. Buscar ou criar um cartão para teste
        cartao = CartaoCredito.query.first()
        if not cartao:
            print("Nenhum cartão encontrado para teste.")
            return

        print(f"Testando Cartão: {cartao.nome}")
        print(f"Limite Original: {cartao.limite_total}")
        
        # Ativar limite emergencial de 10%
        cartao.limite_emergencial_ativo = True
        cartao.perc_limite_emergencial = Decimal('0.10')
        db.session.commit()
        
        print(f"Limite Máximo Total (com 10% emergencial): {cartao.limite_maximo_total}")
        
        if cartao.limite_maximo_total != cartao.limite_total * Decimal('1.1'):
            print("ERRO: Cálculo do limite máximo total incorreto.")
        else:
            print("SUCESSO: Cálculo do limite máximo total correto.")

def test_payment_logic():
    with app.app_context():
        # Simular os argumentos que a rota receberia
        fatura = FaturaCartao.query.filter_by(status='fechada').first()
        if not fatura:
            fatura = FaturaCartao.query.first()
        
        if not fatura:
            print("Nenhuma fatura encontrada para teste.")
            return
            
        banco = Ativo.query.filter_by(tipo=TipoAtivo.BANCO.value).first()
        if not banco:
            print("Nenhum banco encontrado para teste.")
            return
            
        print(f"Testando pagamento da fatura {fatura.competencia}")
        # Apenas verificar se o método aceita os novos argumentos
        print("Verificando assinatura do método realizar_pagamento_fatura...")
        import inspect
        sig = inspect.signature(CreditCardService.realizar_pagamento_fatura)
        print(f"Assinatura: {sig}")
        
        expected_params = ['valor_fatura', 'valor_encargos', 'conta_encargos_id']
        missing = [p for p in expected_params if p not in sig.parameters]
        
        if missing:
            print(f"ERRO: Parâmetros ausentes na assinatura: {missing}")
        else:
            print("SUCESSO: Assinatura do método está correta.")

if __name__ == "__main__":
    test_emergency_limit()
    test_payment_logic()
