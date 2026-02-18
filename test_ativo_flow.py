from app import create_app, db
from app.models import Titulo, Ativo, Entidade, ContaContabil, TipoEntidade, TipoConta, TipoAtivo
from app.services import AssetService
from datetime import datetime
from decimal import Decimal

app = create_app()
with app.app_context():
    # 1. Preparar dados
    fornecedor = Entidade.query.filter_by(tipo=TipoEntidade.FORNECEDOR.value).first()
    conta_ativo = ContaContabil.query.filter_by(tipo=TipoConta.ATIVO.value).first()
    
    if not fornecedor or not conta_ativo:
        print("Dados insuficientes para o teste.")
        exit()
        
    print(f"Testando com Fornecedor: {fornecedor.nome} e Conta: {conta_ativo.nome}")
    
    # 2. Comprar Ativo
    descricao = "Veiculo de Teste " + datetime.now().strftime("%H%M%S")
    ativo = AssetService.comprar_ativo_imobilizado(
        descricao=descricao,
        valor=Decimal("1000.00"),
        entidade_fornecedor=fornecedor,
        data_aquisicao=datetime.now().date(),
        conta_ativo_id=conta_ativo.id,
        tipo_ativo="Veiculo",
        num_parcelas=2,
        valor_juros=Decimal("10.00")
    )
    db.session.commit()
    print(f"Ativo criado: ID {ativo.id}")
    
    # 3. Verificar Títulos
    titulos = Titulo.query.filter_by(ativo_id=ativo.id).all()
    print(f"Títulos vinculados encontrados: {len(titulos)}")
    for t in titulos:
        print(f"  T-ID: {t.id}, AtivoID: {t.ativo_id}")
        
    if len(titulos) == 0:
        print("ERRO: Nenhum título vinculado encontrado!")
    else:
        # 4. Estornar
        print(f"Iniciando estorno do ativo {ativo.id}...")
        success, msg = AssetService.estornar_compra_ativo(ativo.id)
        db.session.commit()
        print(f"Resultado do estorno: {success}, {msg}")
        
        # 5. Verificar se sumiu tudo
        ativo_morto = db.session.get(Ativo, ativo.id)
        titulos_mortos = Titulo.query.filter_by(ativo_id=ativo.id).all()
        print(f"Verificação pós-estorno: Ativo existe? {ativo_morto is not None}, Títulos restantes: {len(titulos_mortos)}")
