from app import create_app, db
from app.models import Titulo, Ativo, Entidade, ContaContabil, TipoEntidade, TipoConta, TipoAtivo, StatusTitulo
from app.services import AssetService
from datetime import datetime
from decimal import Decimal

app = create_app()
with app.app_context():
    # 1. Preparar dados
    fornecedor = Entidade.query.filter_by(tipo=TipoEntidade.FORNECEDOR.value).first()
    conta_ativo = ContaContabil.query.filter_by(tipo=TipoConta.ATIVO.value).first()
    
    # 2. Comprar Ativo de Teste
    descricao = "TESTE TRAVA SEGURANCA " + datetime.now().strftime("%H%M%S")
    ativo = AssetService.comprar_ativo_imobilizado(
        descricao=descricao,
        valor=Decimal("100.00"),
        entidade_fornecedor=fornecedor,
        data_aquisicao=datetime.now().date(),
        conta_ativo_id=conta_ativo.id,
        tipo_ativo="Veiculo",
        num_parcelas=2,
        valor_juros=Decimal("0.00")
    )
    db.session.commit()
    print(f"Ativo de teste criado: ID {ativo.id}")
    
    # 3. Pagar uma parcela
    titulo = Titulo.query.filter_by(ativo_id=ativo.id).first()
    titulo.status = StatusTitulo.PAGO.value
    db.session.commit()
    print(f"Parcela {titulo.id} marcada como PAGA.")
    
    # 4. Tentar Estornar (Deve falhar)
    print("Tentando estornar ativo com parcela paga...")
    success, msg = AssetService.estornar_compra_ativo(ativo.id)
    print(f"Resultado (Esperado falha): {success}, Mensagem: {msg}")
    
    if not success and "Estorne o pagamento primeiro" in msg:
        print("TESTE PASSOU: Trava funcionou corretamente.")
    else:
        print("TESTE FALHOU: O estorno deveria ter sido bloqueado.")
        
    # 5. Limpando para testes futuros (opcional se for banco temp, mas aqui é real)
    # Se falhou o estorno, o ativo ainda existe. Vamos deixar assim para auditoria se necessário
    # ou remover manualmente para o sistema ficar limpo.
    if not success:
        # Resetar para poder deletar
        titulo.status = StatusTitulo.ABERTO.value
        db.session.commit()
        print("Resetando status para remover ativo de teste...")
        success2, msg2 = AssetService.estornar_compra_ativo(ativo.id)
        db.session.commit()
        print(f"Remoção de limpeza: {success2}")
