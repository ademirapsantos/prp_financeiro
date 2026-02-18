from . import db
from .models import ContaContabil, TipoConta, NaturezaConta, TipoEntidade, Entidade, TipoAtivo, Ativo, ConfiguracaoSMTP

def seed_db():
    # Seed para SMTP sempre executa se não existir
    if not ConfiguracaoSMTP.query.first():
        print("Criando configuração SMTP padrão...")
        cfg = ConfiguracaoSMTP(
            smtp_server='smtp.gmail.com',
            smtp_port=587,
            use_tls=True,
            use_ssl=False
        )
        db.session.add(cfg)
        db.session.commit()

    if ContaContabil.query.first():
        return

    # Função helper para criar contas
    def criar_conta(codigo, nome, tipo, natureza, pai=None):
        # Garantir que estamos salvando o valor string
        tipo_val = tipo.value if hasattr(tipo, 'value') else tipo
        natureza_val = natureza.value if hasattr(natureza, 'value') else natureza
        
        conta = ContaContabil(
            codigo=codigo, 
            nome=nome, 
            tipo=tipo_val, 
            natureza=natureza_val, 
            parent_id=pai.id if pai else None
        )
        db.session.add(conta)
        db.session.flush() # Para ter o ID disponível
        return conta

    print("Criando Plano de Contas Hierárquico...")

    # 1. ATIVOS
    root_ativo = criar_conta("1", "Ativos", TipoConta.ATIVO, NaturezaConta.DEVEDORA)
    
    # 1.1 Bancos
    bancos = criar_conta("1.1", "Bancos", TipoConta.ATIVO, NaturezaConta.DEVEDORA, root_ativo)
    criar_conta("1.1.01", "Itaú", TipoConta.ATIVO, NaturezaConta.DEVEDORA, bancos)
    criar_conta("1.1.02", "NuBank", TipoConta.ATIVO, NaturezaConta.DEVEDORA, bancos)
    criar_conta("1.1.03", "Santander", TipoConta.ATIVO, NaturezaConta.DEVEDORA, bancos)
    criar_conta("1.1.04", "Mercado Pago", TipoConta.ATIVO, NaturezaConta.DEVEDORA, bancos)

    # 1.2 Carteiras
    carteiras = criar_conta("1.2", "Carteiras", TipoConta.ATIVO, NaturezaConta.DEVEDORA, root_ativo)
    criar_conta("1.2.01", "Carteira Ademir", TipoConta.ATIVO, NaturezaConta.DEVEDORA, carteiras)
    criar_conta("1.2.02", "Carteira Gabriela", TipoConta.ATIVO, NaturezaConta.DEVEDORA, carteiras)

    # 1.3 Imóvel e Veículo
    criar_conta("1.3", "Imóveis", TipoConta.ATIVO, NaturezaConta.DEVEDORA, root_ativo)
    criar_conta("1.4", "Veículos", TipoConta.ATIVO, NaturezaConta.DEVEDORA, root_ativo)


    # 1.1.05 Clientes (Recebíveis)
    clientes_receber = criar_conta("1.1.05", "Clientes a Receber", TipoConta.ATIVO, NaturezaConta.DEVEDORA, bancos.pai) # Pai é o root_ativo (1) ? Não, 1.1 é Bancos. Clientes é 1.5? 
    # Melhor estruturar: 
    # 1. ATIVO
    #   1.1 Circulante
    #       1.1.01 Caixa e Equivalentes (Bancos)
    #       1.1.02 Clientes a Receber
    #   1.2 Não Circulante (Imobilizado)
    
    # Mas para não quebrar IDs existentes, vou apenas adicionar onde faz sentido no nível 2 ou 1.
    
    # Vamos adicionar Clientes direto no Ativo por enquanto, ou melhor, criar um grupo "Contas a Receber"
    contas_receber = criar_conta("1.5", "Contas a Receber", TipoConta.ATIVO, NaturezaConta.DEVEDORA, root_ativo)
    criar_conta("1.5.01", "Clientes Nacionais", TipoConta.ATIVO, NaturezaConta.DEVEDORA, contas_receber)

    # 2. PASSIVOS
    root_passivo = criar_conta("2", "Passivos", TipoConta.PASSIVO, NaturezaConta.CREDORA)
    
    criar_conta("2.1", "Cartões de Crédito", TipoConta.PASSIVO, NaturezaConta.CREDORA, root_passivo)
    criar_conta("2.2", "Empréstimos", TipoConta.PASSIVO, NaturezaConta.CREDORA, root_passivo)
    
    # Fornecedores
    fornecedores = criar_conta("2.3", "Fornecedores", TipoConta.PASSIVO, NaturezaConta.CREDORA, root_passivo)
    criar_conta("2.3.01", "Fornecedores Nacionais", TipoConta.PASSIVO, NaturezaConta.CREDORA, fornecedores)

    consignado = criar_conta("2.4", "Consignado", TipoConta.PASSIVO, NaturezaConta.CREDORA, root_passivo)
    criar_conta("2.4.01", "NeoConsiga+", TipoConta.PASSIVO, NaturezaConta.CREDORA, consignado)


    # 3. RECEITAS
    root_receita = criar_conta("4", "Receitas", TipoConta.RECEITA, NaturezaConta.CREDORA)
    
    # 3.1 Trabalho Fixo
    trab_fixo = criar_conta("4.1", "Trabalho Fixo", TipoConta.RECEITA, NaturezaConta.CREDORA, root_receita)
    criar_conta("4.1.01", "T.I.", TipoConta.RECEITA, NaturezaConta.CREDORA, trab_fixo)
    criar_conta("4.1.02", "Saúde", TipoConta.RECEITA, NaturezaConta.CREDORA, trab_fixo)

    # 3.2 Freelancers
    freela = criar_conta("4.2", "Freelancers", TipoConta.RECEITA, NaturezaConta.CREDORA, root_receita)
    criar_conta("4.2.01", "Temporário T.I.", TipoConta.RECEITA, NaturezaConta.CREDORA, freela)
    criar_conta("4.2.02", "Temporário Saúde", TipoConta.RECEITA, NaturezaConta.CREDORA, freela)

    criar_conta("4.3", "Rendimentos de Investimentos", TipoConta.RECEITA, NaturezaConta.CREDORA, root_receita)


    # 4. DESPESAS
    root_despesa = criar_conta("5", "Despesas", TipoConta.DESPESA, NaturezaConta.DEVEDORA)
    
    # 4.1 Fixas
    fixas = criar_conta("5.1", "Fixas", TipoConta.DESPESA, NaturezaConta.DEVEDORA, root_despesa)
    criar_conta("5.1.01", "Condução", TipoConta.DESPESA, NaturezaConta.DEVEDORA, fixas)

    # 4.2 Imóvel
    desp_imovel = criar_conta("5.2", "Despesas Imóvel", TipoConta.DESPESA, NaturezaConta.DEVEDORA, root_despesa)
    criar_conta("5.2.01", "Energia", TipoConta.DESPESA, NaturezaConta.DEVEDORA, desp_imovel)
    criar_conta("5.2.02", "Água", TipoConta.DESPESA, NaturezaConta.DEVEDORA, desp_imovel)
    criar_conta("5.2.03", "Internet", TipoConta.DESPESA, NaturezaConta.DEVEDORA, desp_imovel)
    criar_conta("5.2.04", "Aluguel", TipoConta.DESPESA, NaturezaConta.DEVEDORA, desp_imovel)

    criar_conta("5.3", "Variáveis", TipoConta.DESPESA, NaturezaConta.DEVEDORA, root_despesa)

    # 5. PATRIMÔNIO LÍQUIDO (Necessário para balanço fechar inicialmente)
    root_pl = criar_conta("3", "Patrimônio Líquido", TipoConta.PATRIMONIO_LIQUIDO, NaturezaConta.CREDORA)
    criar_conta("3.1", "Capital Social", TipoConta.PATRIMONIO_LIQUIDO, NaturezaConta.CREDORA, root_pl)


    db.session.commit()
    print("Plano de Contas Hierárquico criado com sucesso.")

    # Seeds de Exemplo (Entidades e Ativos)
    # Buscar contas para vincular
    conta_itau = ContaContabil.query.filter_by(nome="Itaú").first()
    conta_ti = ContaContabil.query.filter_by(nome="T.I.").first() # Receita
    
    if conta_itau:
        banco = Ativo(descricao="Conta Itaú Principal", tipo=TipoAtivo.BANCO.value, valor_atual=0, conta_contabil_id=conta_itau.id)
        db.session.add(banco)
    
    if conta_ti:
        # Entidade Empregador
        empresa = Entidade(nome="Empresa TI S.A.", tipo=TipoEntidade.CLIENTE.value, conta_contabil_id=conta_ti.id)
        db.session.add(empresa)

    db.session.commit()
