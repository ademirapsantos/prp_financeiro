from app import create_app, db
from app.models import Ativo, ContaContabil, PartidaDiario
from decimal import Decimal

def test_cadastro_banco():
    app = create_app()
    with app.app_context():
        print("--- 1. Simulando Cadastro de Banco ---")
        # Simular o que a rota faz... ou chamar a rota?
        # Vamos testar a lógica que implementamos na rota (idealmente deveria estar num Service, mas está na Rota)
        # Como está na rota, vamos usar o test_client do Flask.
        
        client = app.test_client()
        
        novo_banco_dados = {
            'nome': 'Banco Inter Teste',
            'saldo_inicial': '100.00'
        }
        
        print(f"Enviando POST com: {novo_banco_dados}")
        response = client.post('/financeiro/bancos/novo', data=novo_banco_dados, follow_redirects=True)
        
        if response.status_code != 200:
             print(f"❌ Erro na requisição: Status {response.status_code}")
             print(response.data.decode('utf-8'))
             return

        print("--- 2. Verificações no Banco de Dados ---")
        
        # 2.1 Verificar Ativo
        banco = Ativo.query.filter_by(descricao='Banco Inter Teste').first()
        if banco:
            print(f"✅ Ativo Criado: {banco.descricao} (ID: {banco.id})")
        else:
            print("❌ Ativo não encontrado.")
            return

        # 2.2 Verificar Conta Contábil
        if banco.conta_contabil:
             print(f"✅ Conta Contábil Vinculada: {banco.conta_contabil.codigo} - {banco.conta_contabil.nome}")
             # Verificar se é filha de 1.1.01
             if banco.conta_contabil.codigo.startswith('1.1.01'):
                  print("✅ Hierarquia Correta (1.1.01...)")
             else:
                  print(f"❌ Hierarquia Incorreta: {banco.conta_contabil.codigo}")
        else:
             print("❌ Conta contábil não vinculada.")

        # 2.3 Verificar Saldo Inicial
        # Deve haver partidas na conta
        partidas = PartidaDiario.query.filter_by(conta_id=banco.conta_contabil_id).all()
        total_debito = sum(p.valor for p in partidas if p.tipo == 'D')
        if total_debito == Decimal('100.00'):
             print("✅ Lançamento de Saldo Inicial (Débito) OK")
        else:
             print(f"❌ Saldo Inicial incorreto. Débitos encontrados: {total_debito}")

if __name__ == "__main__":
    test_cadastro_banco()
