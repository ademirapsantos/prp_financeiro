from app import create_app
from app.models import Entidade, TipoEntidade, db

def test_crud_entidades():
    app = create_app()
    app.config['PROPAGATE_EXCEPTIONS'] = True
    app.config['TESTING'] = True
    client = app.test_client()
    
    print("--- 1. Testando Listagem Vazia (ou com seeds) ---")
    print(f"DB URI: {app.config['SQLALCHEMY_DATABASE_URI']}")
    import os
    print(f"CWD: {os.getcwd()}")
    if os.path.exists('instance/data/prp_financeiro.db'):
        print("Arquivo encontrado em INSTANCE/data/prp_financeiro.db")
    if os.path.exists('data/prp_financeiro.db'):
        print("Arquivo encontrado em data/prp_financeiro.db")

    with app.app_context():
        print(f"Colunas Entidade: {Entidade.__table__.columns.keys()}")
    
    resp = client.get('/entidades/')
    print(f"Lista Status: {resp.status_code}")
    
    print("--- 2. Criando Novo Fornecedor ---")
    # Dados do fomulário
    data = {
        'nome': 'Fornecedor de Teste Auto',
        'tipo': TipoEntidade.FORNECEDOR.value, # 'Fornecedor'
        'documento': '12345678000199'
    }
    
    resp = client.post('/entidades/nova', data=data, follow_redirects=True)
    print(f"Post Status: {resp.status_code}")
    
    # Verificar se foi criado no banco
    with app.app_context():
        novo = Entidade.query.filter_by(nome='Fornecedor de Teste Auto').first()
        if novo:
            print(f"✅ Entidade Criada: {novo.nome} ({novo.tipo})")
            print(f"✅ Conta Contábil Vinculada: {novo.conta_contabil.nome if novo.conta_contabil else 'NENHUMA ❌'}")
            
            # Validar se a conta vinculada é de Fornecedores
            if novo.conta_contabil and 'Fornecedores' in novo.conta_contabil.nome:
                print("✅ Vínculo Contábil Correto")
            else:
                print(f"❌ Vínculo Contábil Incorreto ou vazio: {novo.conta_contabil.nome if novo.conta_contabil else 'None'}")
        else:
            print("❌ Entidade não encontrada no banco.")

if __name__ == "__main__":
    test_crud_entidades()
