from app import create_app, db
from app.models import Ativo, ContaContabil

def test_edicao_banco():
    app = create_app()
    with app.app_context():
        # 1. Encontrar um banco existente (criado no teste anterior)
        banco = Ativo.query.filter_by(descricao='Banco Inter Teste').first()
        if not banco:
            print("❌ Banco para teste não encontrado. Execute o cadastro primeiro.")
            return

        print(f"--- 1. Banco Atual: {banco.descricao} (ID: {banco.id}) ---")
        
        client = app.test_client()
        
        # 2. Simular Edição
        dados_edicao = {
            'nome': 'Banco Inter Atualizado'
        }
        
        print(f"Enviando POST de edição para /financeiro/bancos/editar/{banco.id}")
        response = client.post(f'/financeiro/bancos/editar/{banco.id}', data=dados_edicao, follow_redirects=True)
        
        if response.status_code != 200:
             print(f"❌ Erro na requisição: Status {response.status_code}")
             return

        # 3. Verificar Mudanças
        # Refresh do objeto
        db.session.refresh(banco)
        
        print("--- 2. Verificações após Edição ---")
        if banco.descricao == 'Banco Inter Atualizado':
            print("✅ Descrição do Ativo atualizada.")
        else:
            print(f"❌ Descrição do Ativo incorreta: {banco.descricao}")

        if banco.conta_contabil and banco.conta_contabil.nome == 'Banco Inter Atualizado':
            print("✅ Nome da Conta Contábil atualizada.")
        else:
            nome_cc = banco.conta_contabil.nome if banco.conta_contabil else 'N/A'
            print(f"❌ Nome da Conta Contábil incorreto: {nome_cc}")

if __name__ == "__main__":
    test_edicao_banco()
