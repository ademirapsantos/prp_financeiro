from app import create_app, db
from app.models import ContaContabil, Ativo, Entidade, TipoEntidade, Titulo, StatusTitulo, TipoTransacao, LivroDiario, TipoConta, NaturezaConta, TipoTitulo, TipoAtivo, TipoAtivo
from app.services import FinancialService, AssetService, AccountingService
from datetime import datetime, timedelta
import sys

app = create_app()

with app.app_context():
    print("--- 1. Preparação de Cenário ---")
    # Buscar contas chave
    try:
        conta_receita_ti = ContaContabil.query.filter_by(nome="T.I.").first()
        conta_ativo_itau = ContaContabil.query.filter_by(nome="Itaú").first()
        conta_imovel = ContaContabil.query.filter_by(nome="Imóveis").first()
        
        # Criar Cliente e Fornecedor Teste
        # Criar Cliente e Fornecedor Teste
        # Cliente
        cliente = Entidade(
            nome="Cliente Teste SA", 
            tipo=TipoEntidade.CLIENTE.value, 
            conta_contabil_id=conta_receita_ti.id
        )
        # Fornecedor
        fornecedor = Entidade(
            nome="Construtora XYZ", 
            tipo=TipoEntidade.FORNECEDOR.value, 
            conta_contabil_id=conta_imovel.id
        ) # Vinculando provisoriamente
        
        db.session.add(cliente)
        db.session.add(fornecedor)
        db.session.commit()
    except Exception as e:
        print(f"Erro na preparação: {e}")
        sys.exit(1)

    print("--- 2. Teste: Faturar Venda (Contas a Receber) ---")
    try:
        # Simular Venda: Credita Receita (TI), Debita Cliente (Cliente Teste)
        # OBS: A conta do cliente para onde vai o débito normalmente é "Contas a Receber" (Ativo).
        # No nosso modelo simplificado, o cliente TEM uma conta contábil vinculada.
        # Se a conta vinculada ao cliente for "Receita", temos um problema: D: Receita / C: Receita?
        # CORREÇÃO MODELAGEM: Cliente deve estar vinculado a "Clientes a Receber" (Ativo Circulante).
        # A Receita (Resultado) vem do SERVIÇO prestado, não da entidade.
        
        # Ajuste on-the-fly para o teste funcionar com a lógica atual:
        # Vamos assumir que FinancialService.criar_titulo_pagar é para DESPESAS.
        # Precisamos de um criar_titulo_receber.
        pass
    except Exception as e:
        print(f"Erro: {e}")

    # Como não tenho criar_titulo_receber no FinancialService ainda, vou implementar manualmente no teste e depois promover pro service.
    
    # CENÁRIO CORRIGIDO:
    # 1. Venda de Serviço -> Título a Receber
    # Partidas: 
    #   D: Clientes a Receber (Ativo)
    #   C: Receita de Serviços (Resultado)
    
    # Criar conta "Clientes a Receber" que faltou no seed
    conta_clientes_receber = ContaContabil.query.filter_by(codigo="1.1.99").first()
    if not conta_clientes_receber:
        conta_clientes_receber = ContaContabil(
            codigo="1.1.99", 
            nome="Clientes a Receber", 
            tipo=TipoConta.ATIVO, 
            natureza=NaturezaConta.DEVEDORA, 
            parent_id=1
        )
        db.session.add(conta_clientes_receber)
        db.session.commit()
    
    # Atualizar cliente para usar essa conta como "Conta do Parceiro" (onde fica o débito antes de pagar)
    cliente.conta_contabil_id = conta_clientes_receber.id
    db.session.commit()

    print("--- 2. Realizando Venda ---")
    # Verificar se título já existe para não duplicar
    titulo_venda = Titulo.query.filter_by(descricao="Serviço de Consultoria", status=StatusTitulo.ABERTO.value).first()
    if not titulo_venda:
        titulo_venda = Titulo(
            entidade_id=cliente.id,
            descricao="Serviço de Consultoria",
            valor=5000.00,
            data_vencimento=datetime.utcnow() + timedelta(days=10),
            tipo=TipoTitulo.RECEBER.value, # Usando Enum.value
            status=StatusTitulo.ABERTO.value
        )
        db.session.add(titulo_venda)
        db.session.flush() # Gerar ID
        
        # Lançamento: D: Clientes a Receber / C: Receita T.I.
        partidas_venda = [
            {'conta_id': conta_clientes_receber.id, 'tipo': 'D', 'valor': 5000.00},
            {'conta_id': conta_receita_ti.id, 'tipo': 'C', 'valor': 5000.00}
        ]
        AccountingService.criar_lancamento("Venda Consultoria", datetime.utcnow(), partidas_venda)
        print("✅ Venda Faturada e Contabilizada.")
    else:
        print("⚠️ Venda já existente, pulando criação.")

    print("--- 3. Teste: Recebimento (Liquidação) ---")
    # Receber no Itaú
    try:
        transacao = FinancialService.liquidar_titulo(titulo_venda, 1, datetime.utcnow()) # ID 1 assumindo ser um ativo valido (preciso pegar o ID do Itau)
        # Pegar ativo itau
        ativo_itau = Ativo.query.filter(Ativo.descricao.like('%Itaú%')).first()
        if not ativo_itau:
             # Criar se não existir (o seed cria, mas vamos garantir)
             ativo_itau = Ativo(descricao="Banco Itaú", tipo="Banco", conta_contabil_id=conta_ativo_itau.id)
             db.session.add(ativo_itau)
             db.session.commit()
             
        transacao = FinancialService.liquidar_titulo(titulo_venda, ativo_itau.id, datetime.utcnow())
        print(f"✅ Título Liquidado. Transação ID: {transacao.id}")
        
        # Verificar saldo
        # Clientes a Receber deve estar zerado (D 5000, C 5000)
        # Itaú deve ter D 5000
        print("✅ Liquidação contabilizada.")
    except Exception as e:
        print(f"❌ Erro na liquidação: {e}")
        import traceback
        traceback.print_exc()

    print("--- Resumo Contábil ---")
    diarios = LivroDiario.query.all()
    for d in diarios:
        print(f"Diário {d.id}: {d.historico} - {d.data}")
        for p in d.partidas:
            print(f"  - {p.tipo} {p.valor} | Conta: {p.conta.nome}")

