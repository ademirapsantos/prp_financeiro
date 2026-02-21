from . import db
from .models import LivroDiario, PartidaDiario, Titulo, TransacaoFinanceira, TipoTransacao, StatusTitulo, Ativo, ContaContabil, TipoConta, NaturezaConta, TipoTitulo, TipoAtivo, Configuracao
from datetime import datetime
from decimal import Decimal

class AccountingService:
    @staticmethod
    def _normalizar_valor(valor):
        from decimal import Decimal, ROUND_HALF_UP
        return Decimal(valor).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    
    @staticmethod
    def _validar_natureza_conta(conta, tipo_partida):
        """
        Valida se a conta pode receber Débito ou Crédito.
        Contas de Resultado (Receitas e Despesas) são rígidas.
        Contas Patrimoniais (Ativo, Passivo, PL) aceitam ambos os lados para aumento/redução saldo.
        """
        tipo = conta.tipo
        
        # Regras para Contas de Resultado (Nominais)
        if tipo == TipoConta.RECEITA.value and tipo_partida == 'D':
            raise ValueError(f"Conta de Receita {conta.codigo} não aceita Débito (Natureza Credora).")
        
        if tipo == TipoConta.DESPESA.value and tipo_partida == 'C':
            raise ValueError(f"Conta de Despesa {conta.codigo} não aceita Crédito (Natureza Devedora).")
        
        # Contas Patrimoniais: Ativo, Passivo e PL aceitam D e C.
        pass

    @staticmethod
    def criar_lancamento(historico, data, partidas):
        """
        Cria um lançamento no Livro Diário com validação de Partida Dobrada e Domínio Contábil.
        partidas: Lista de dicionarios {'conta_id': int, 'tipo': 'D'/'C', 'valor': Decimal}
        """
        # 1. Padronizar Valores e Validar Soma Zero (Débito == Crédito)
        total_debito = Decimal('0.00')
        total_credito = Decimal('0.00')
        
        partidas_processadas = []
        for p in partidas:
            # Garantir 2 casas decimais com arredondamento contábil
            valor_padrao = AccountingService._normalizar_valor(p['valor'])
            
            if p['tipo'] == 'D':
                total_debito += valor_padrao
            else:
                total_credito += valor_padrao
                
            partidas_processadas.append({
                'conta_id': p['conta_id'],
                'tipo': p['tipo'],
                'valor': valor_padrao
            })

        if abs(total_debito - total_credito) > Decimal('0.00'):
            raise ValueError(f"O lançamento não balanceia! Débito: {total_debito}, Crédito: {total_credito}")

        # 2. Criar Lançamento Mestre
        diario = LivroDiario(historico=historico, data=data)
        db.session.add(diario)
        db.session.flush()

        # 3. Validar e Criar Partidas
        for p in partidas_processadas:
            conta = db.session.get(ContaContabil, p['conta_id'])
            if not conta:
                raise ValueError(f"Conta ID {p['conta_id']} não encontrada.")
            
            # Validação Crítica: Apenas contas analíticas aceitam lançamentos
            if not conta.is_analitica:
                raise ValueError(f"Conta {conta.codigo} ({conta.nome}) é SINTÉTICA e não aceita lançamentos.")
            
            # Validação de Natureza (Regras de Domínio)
            AccountingService._validar_natureza_conta(conta, p['tipo'])

            partida = PartidaDiario(
                diario_id=diario.id, 
                conta_id=p['conta_id'], 
                tipo=p['tipo'], 
                valor=p['valor']
            )
            db.session.add(partida)
        
        return diario

    @staticmethod
    def registrar_liquidacao_titulo(titulo, banco, data_pagamento, valor_desconto=0, conta_desconto_id=None):
        """
        Inteligência de Domínio: Decide as partidas contábeis para a liquidação de um título.
        Suporta descontos (obtidos ou concedidos).
        """
        # 1. Resolver Conta da Categoria (Resultado/Patrimonial do Ativo)
        if titulo.ativo_id and titulo.ativo and titulo.ativo.conta_contabil_id:
            conta_category_id = titulo.ativo.conta_contabil_id
        else:
            conta_category_id = titulo.entidade.conta_resultado_id
            if not conta_category_id:
                if titulo.tipo == 'Pagar' or titulo.tipo == TipoTitulo.PAGAR.value:
                    conta_category_id = titulo.entidade.conta_compra_id
                else:
                    conta_category_id = titulo.entidade.conta_venda_id

        if not conta_category_id:
            raise ValueError(f"Entidade '{titulo.entidade.nome}' não possui conta de categoria configurada.")

        # 2. Montar Partidas
        valor_liquido = titulo.valor - Decimal(str(valor_desconto))
        partidas = []
        
        if titulo.tipo == 'Pagar' or titulo.tipo == TipoTitulo.PAGAR.value:
            # PAGAMENTO COM DESCONTO:
            # D: Categoria (Bruto)
            # C: Banco (Liquido)
            # C: Descontos Obtidos (Desconto)
            partidas.append({'conta_id': conta_category_id, 'tipo': 'D', 'valor': titulo.valor})
            partidas.append({'conta_id': banco.conta_contabil_id, 'tipo': 'C', 'valor': valor_liquido})
            if valor_desconto > 0 and conta_desconto_id:
                partidas.append({'conta_id': conta_desconto_id, 'tipo': 'C', 'valor': valor_desconto})
        else: # RECEBIMENTO COM DESCONTO:
            # D: Banco (Liquido)
            # D: Descontos Concedidos (Desconto)
            # C: Categoria (Bruto)
            partidas.append({'conta_id': banco.conta_contabil_id, 'tipo': 'D', 'valor': valor_liquido})
            if valor_desconto > 0 and conta_desconto_id:
                partidas.append({'conta_id': conta_desconto_id, 'tipo': 'D', 'valor': valor_desconto})
            partidas.append({'conta_id': conta_category_id, 'tipo': 'C', 'valor': titulo.valor})

        # 3. Executar Lançamento
        return AccountingService.criar_lancamento(
            historico=f"Liq. Titulo {titulo.id} - {titulo.descricao}",
            data=data_pagamento,
            partidas=partidas
        )

    @staticmethod
    def registrar_estorno_liquidacao(titulo, banco):
        """
        Inteligência de Domínio: Decide as partidas contábeis para o estorno de uma liquidação.
        Usa lançamentos inversos para manter a trilha de auditoria.
        """
        # 1. Resolver Conta da Categoria
        if titulo.ativo_id and titulo.ativo and titulo.ativo.conta_contabil_id:
            conta_category_id = titulo.ativo.conta_contabil_id
        else:
            conta_category_id = titulo.entidade.conta_contabil_id 
            if not conta_category_id:
                if titulo.tipo == 'Pagar' or titulo.tipo == TipoTitulo.PAGAR.value:
                    c_padrao = ContaContabil.query.filter_by(codigo='2.3.01').first()
                    if c_padrao: conta_category_id = c_padrao.id
                else:
                    c_padrao = ContaContabil.query.filter_by(codigo='1.5.01').first()
                    if c_padrao: conta_category_id = c_padrao.id

        if not conta_category_id:
            raise ValueError(f"Não foi possível localizar a conta de contrapartida para o estorno de ID {titulo.id}.")

        # 2. Montar Partidas Inversas
        if titulo.tipo == 'Pagar' or titulo.tipo == TipoTitulo.PAGAR.value:
            # Estorno de Pagamento (Original: D: Despesa / C: Banco)
            # Inverso: D: Banco / C: Contrapartida (Fornecedor/Patrimonial)
            partidas = [
                {'conta_id': banco.conta_contabil_id, 'tipo': 'D', 'valor': titulo.valor},
                {'conta_id': conta_category_id, 'tipo': 'C', 'valor': titulo.valor}
            ]
        else: # Estorno de Recebimento
            # Original: D: Banco / C: Receita
            # Inverso: D: Cliente (Patrimonial) / C: Banco
            partidas = [
                {'conta_id': conta_category_id, 'tipo': 'D', 'valor': titulo.valor},
                {'conta_id': banco.conta_contabil_id, 'tipo': 'C', 'valor': titulo.valor}
            ]

        # 3. Executar Lançamento
        return AccountingService.criar_lancamento(
            historico=f"ESTORNO LIQ: {titulo.descricao} (ID: {titulo.id})",
            data=datetime.utcnow(),
            partidas=partidas
        )

class FinancialService:
    @staticmethod
    def criar_titulo_pagar(entidade, descricao, valor, data_vencimento):
        """
        Cria um título a pagar e lança a provisão na contabilidade.
        D: Despesa (Resultado da Entidade ou conta_compra_id)
        C: Fornecedores a Pagar (Patrimonial da Entidade ou Default 2.3.01)
        """
        # 1. Resolver Contas
        conta_p_id = entidade.conta_contabil_id # Patrimonial (Passivo)
        conta_r_id = entidade.conta_resultado_id # Resultado (Despesa)
        
        # Fallback para nova lógica simplificada
        if entidade.tipo == 'Fornecedor':
            if not conta_r_id:
                conta_r_id = entidade.conta_compra_id
            if not conta_p_id:
                # Buscar conta padrão: Fornecedores Nacionais (2.3.01)
                c_padrao = ContaContabil.query.filter_by(codigo='2.3.01').first()
                if c_padrao:
                    conta_p_id = c_padrao.id

        if not conta_p_id or not conta_r_id:
            raise ValueError(f"Entidade '{entidade.nome}' não possui as contas automáticas (Patrimonial e Resultado) configuradas.")

        # 2. Criar Título
        titulo = Titulo(
            entidade_id=entidade.id,
            descricao=descricao,
            valor=valor,
            data_vencimento=data_vencimento,
            tipo=TipoTitulo.PAGAR.value,
            status=StatusTitulo.ABERTO.value
        )
        db.session.add(titulo)
        
        return titulo

    @staticmethod
    def criar_titulo_receber(entidade, descricao, valor, data_vencimento):
        """
        Cria um título a receber e lança a provisão na contabilidade.
        D: Clientes a Receber (Patrimonial da Entidade ou Default 1.5.01)
        C: Receita (Resultado da Entidade ou conta_venda_id)
        """
        # 1. Resolver Contas
        conta_p_id = entidade.conta_contabil_id # Patrimonial (Ativo)
        conta_r_id = entidade.conta_resultado_id # Resultado (Receita)
        
        # Fallback para nova lógica simplificada
        if entidade.tipo == 'Cliente':
            if not conta_r_id:
                conta_r_id = entidade.conta_venda_id
            if not conta_p_id:
                # Buscar conta padrão: Clientes a Receber (1.5.01)
                c_padrao = ContaContabil.query.filter_by(codigo='1.5.01').first()
                if c_padrao:
                    conta_p_id = c_padrao.id

        if not conta_p_id or not conta_r_id:
            raise ValueError(f"Entidade '{entidade.nome}' não possui as contas automáticas (Patrimonial e Resultado) configuradas.")

        # 2. Criar Título
        titulo = Titulo(
            entidade_id=entidade.id,
            descricao=descricao,
            valor=valor,
            data_vencimento=data_vencimento,
            tipo=TipoTitulo.RECEBER.value,
            status=StatusTitulo.ABERTO.value
        )
        db.session.add(titulo)
        
        return titulo

    @staticmethod
    def liquidar_titulo(titulo, conta_banco_id, data_pagamento, valor_desconto=0):
        """
        Liquida um título utilizando saldo de um Banco (Ativo).
        A inteligência das partidas contábeis foi movida para o AccountingService.
        """
        if titulo.status == StatusTitulo.PAGO.value:
            raise ValueError("Título já está pago.")

        # 1. Validar e Calcular Valores
        valor_desconto_dec = Decimal(str(valor_desconto))
        if valor_desconto_dec < 0:
            raise ValueError("Desconto não pode ser negativo.")
        if valor_desconto_dec > titulo.valor:
            raise ValueError("Desconto não pode ser maior que o valor do título.")
            
        valor_liquido = titulo.valor - valor_desconto_dec

        # Buscar o ativo banco
        banco = db.session.get(Ativo, conta_banco_id)
        if not banco or not banco.conta_contabil_id:
            raise ValueError("Banco inválido ou sem conta contábil.")

        # 2. Buscar Conta de Desconto configurada
        conta_desconto_id = None
        if valor_desconto_dec > 0:
            if titulo.tipo == 'Pagar' or titulo.tipo == TipoTitulo.PAGAR.value:
                chave_config = 'CONTA_DESCONTO_OBTIDO_ID'
            else:
                chave_config = 'CONTA_DESCONTO_CONCEDIDO_ID'
                
            res_config = Configuracao.query.filter_by(chave=chave_config).first()
            if not res_config or not res_config.valor:
                label_tipo = "Obtidos (Receita)" if chave_config == 'CONTA_DESCONTO_OBTIDO_ID' else "Concedidos (Despesa)"
                raise ValueError(f"Configure a conta de 'Descontos {label_tipo}' nos Parâmetros do Sistema (Chave: {chave_config}) antes de aplicar descontos.")
            conta_desconto_id = int(res_config.valor)

        # 3. Atualizar Saldo e Status (Financeiro)
        if titulo.tipo == 'Pagar' or titulo.tipo == TipoTitulo.PAGAR.value:
            banco.valor_atual -= valor_liquido
            tipo_transacao = TipoTransacao.PAGAMENTO.value
        else:
            banco.valor_atual += valor_liquido
            tipo_transacao = TipoTransacao.RECEBIMENTO.value

        titulo.status = StatusTitulo.PAGO.value
        
        # 4. Criar Transação Financeira (Extrato)
        transacao = TransacaoFinanceira(
            titulo_id=titulo.id,
            ativo_id=banco.id,
            tipo=tipo_transacao,
            valor=valor_liquido, # Valor que saiu/entrou no banco
            valor_bruto=titulo.valor,
            valor_desconto=valor_desconto_dec,
            valor_liquido=valor_liquido,
            data=data_pagamento
        )
        db.session.add(transacao)
        db.session.flush()

        # 5. Gerar Contabilidade (Domínio Contábil)
        diario = AccountingService.registrar_liquidacao_titulo(
            titulo=titulo, 
            banco=banco, 
            data_pagamento=data_pagamento,
            valor_desconto=valor_desconto_dec,
            conta_desconto_id=conta_desconto_id
        )
        diario.transacao_id = transacao.id # Vínculo Reverso
        
        return transacao

    @staticmethod
    def estornar_titulo(titulo, motivo="Cancelamento"):
        """
        Anula contabilmente um título e sua liquidação (se houver).
        A inteligência do estorno foi movida para o AccountingService.
        """
        if titulo.status == StatusTitulo.CANCELADO.value:
            raise ValueError("Título já está cancelado.")

        # 1. Se estiver Pago, estornar a Liquidação primeiro
        if titulo.status == StatusTitulo.PAGO.value:
            # Buscar a última transação de liquidação
            transacao = TransacaoFinanceira.query.filter_by(titulo_id=titulo.id).order_by(TransacaoFinanceira.data.desc()).first()
            if transacao and transacao.ativo:
                banco = transacao.ativo
                
                # 1.1 Inverter Contabilmente a Liquidação (Domínio Contábil)
                AccountingService.registrar_estorno_liquidacao(titulo, banco)
                
                # 1.2 Estornar Saldo Bancário (Financeiro)
                if titulo.tipo == 'Pagar' or titulo.tipo == TipoTitulo.PAGAR.value:
                    banco.valor_atual += titulo.valor
                else:
                    banco.valor_atual -= titulo.valor

        # 2. Cancelar o Título
        titulo.status = StatusTitulo.CANCELADO.value
        titulo.motivo_cancelamento = motivo
        
        return titulo

    @staticmethod
    def registrar_movimentacao_outros(entidade, descricao, valor, banco_id, data_contabil, data_vencimento_base, tipo_mov, num_parcelas=1, categoria_contrapartida='PASSIVO', conta_pl_id=None):
        """
        Registra movimentação de fluxo de caixa (Tomar ou Emprestar dinheiro).
        tipo_mov: 'Receber' (Entrada no Banco) ou 'Pagar' (Saída do Banco)
        """
        from datetime import date
        import calendar

        def add_months(sourcedate, months):
            month = sourcedate.month - 1 + months
            year = sourcedate.year + month // 12
            month = month % 12 + 1
            day = min(sourcedate.day, calendar.monthrange(year, month)[1])
            return date(year, month, day)

        if not entidade:
            raise ValueError("Uma Entidade (Pessoa) deve ser selecionada.")

        # 1. Buscar Banco
        banco = db.session.get(Ativo, banco_id)
        if not banco or not banco.conta_contabil_id:
            raise ValueError("Banco inválido ou sem conta contábil.")

        # 2. Definir Conta de Contrapartida baseada no fluxo e tipo
        if categoria_contrapartida == 'PL':
            if not conta_pl_id: raise ValueError("Selecione a conta de PL.")
            final_conta_contra_id = conta_pl_id
        else:
            # DINHEIRO ENTRA (Tomar Emprestado) -> Contrapartida é a conta de 'Dívida/Compra'
            if tipo_mov == 'Receber':
                final_conta_contra_id = entidade.conta_compra_id
                if not final_conta_contra_id:
                    raise ValueError(f"Entidade '{entidade.nome}' não tem conta de 'Dívida' (Pagar) configurada.")
            # DINHEIRO SAI (Conceder Emprestimo) -> Contrapartida é a conta de 'Direito/Venda/Receita'
            else:
                final_conta_contra_id = entidade.conta_venda_id
                if not final_conta_contra_id:
                    raise ValueError(f"Entidade '{entidade.nome}' não tem conta de 'Direito' (Receber) configurada.")

        partidas = []
        historico_resumo = ""
        
        if tipo_mov == 'Receber': # ENTRADA NO BANCO ($)
            historico_resumo = f"Entrada ($): {descricao}"
            partidas = [
                {'conta_id': banco.conta_contabil_id, 'tipo': 'D', 'valor': valor},
                {'conta_id': final_conta_contra_id, 'tipo': 'C', 'valor': valor}
            ]
            banco.valor_atual += valor
        else: # SAÍDA DO BANCO ($)
            historico_resumo = f"Saída ($): {descricao}"
            partidas = [
                {'conta_id': final_conta_contra_id, 'tipo': 'D', 'valor': valor},
                {'conta_id': banco.conta_contabil_id, 'tipo': 'C', 'valor': valor}
            ]
            banco.valor_atual -= valor

        diario = AccountingService.criar_lancamento(
            historico=f"FINANCEIRO: {historico_resumo} (Entidade: {entidade.nome})",
            data=data_contabil,
            partidas=partidas
        )

        # 4. Transação Financeira (Extrato)
        transacao = TransacaoFinanceira(
            ativo_id=banco.id,
            tipo=TipoTransacao.RECEBIMENTO.value if tipo_mov == 'Receber' else TipoTransacao.PAGAMENTO.value, 
            valor=valor,
            data=data_contabil
        )
        db.session.add(transacao)
        diario.transacao_id = transacao.id 

        # 5. Criar Títulos (Parcelas)
        num_parcelas = int(num_parcelas)
        valor_parcela = valor / num_parcelas
        
        for i in range(1, num_parcelas + 1):
            vencimento = add_months(data_vencimento_base.date(), i - 1)
            desc_parcela = f"{descricao} ({i}/{num_parcelas})" if num_parcelas > 1 else descricao
            
            titulo = Titulo(
                entidade_id=entidade.id,
                descricao=desc_parcela,
                valor=valor_parcela,
                data_vencimento=vencimento,
                tipo='Pagar' if tipo_mov == 'Receber' else 'Receber', # Se tomei $, devo pagar parcelas
                status=StatusTitulo.ABERTO.value,
                parcela_atual=i if num_parcelas > 1 else None,
                total_parcelas=num_parcelas if num_parcelas > 1 else None
            )
            db.session.add(titulo)

        return transacao

    @staticmethod
    def realizar_transferencia(conta_origem_id, conta_destino_id, valor, data, descricao):
        """
        Realiza transferência entre duas contas do Ativo (Bancos/Caixa).
        """
        if conta_origem_id == conta_destino_id:
            raise ValueError("Contas de origem e destino devem ser diferentes.")

        # Validar Contas
        conta_origem = db.session.get(ContaContabil, conta_origem_id)
        conta_destino = db.session.get(ContaContabil, conta_destino_id)
        
        if not conta_origem or not conta_destino:
             raise ValueError("Conta de origem ou destino inválida.")

        # Lógica de Partidas
        partidas = [
            {'conta_id': conta_destino_id, 'tipo': 'D', 'valor': valor},
            {'conta_id': conta_origem_id, 'tipo': 'C', 'valor': valor}
        ]

        # Atualizar Saldos dos Ativos (se vinculados)
        ativo_origem = Ativo.query.filter_by(conta_contabil_id=conta_origem_id).first()
        ativo_destino = Ativo.query.filter_by(conta_contabil_id=conta_destino_id).first()

        if ativo_origem: ativo_origem.valor_atual -= valor
        if ativo_destino: ativo_destino.valor_atual += valor
        
        # Lançamento Contábil
        diario = AccountingService.criar_lancamento(
            historico=f"Transf: {descricao}",
            data=data,
            partidas=partidas
        )
        
        transacao = TransacaoFinanceira(
            titulo_id=None,
            ativo_id=ativo_origem.id if ativo_origem else None,
            tipo=TipoTransacao.TRANSFERENCIA.value,
            valor=valor,
            data=data
        )
        db.session.add(transacao)
        db.session.flush() 
        
        diario.transacao_id = transacao.id
        
        return transacao

    @staticmethod
    def realizar_transferencia_generica(conta_debito_id, conta_credito_id, valor, historico, data):
        """
        Realiza um lançamento contábil simples entre duas contas.
        """
        # Partidas
        partidas = [
            {'conta_id': conta_debito_id, 'tipo': 'D', 'valor': valor},
            {'conta_id': conta_credito_id, 'tipo': 'C', 'valor': valor}
        ]
        
        # Contabilidade
        diario = AccountingService.criar_lancamento(
            historico=historico,
            data=data,
            partidas=partidas
        )
        
        return diario

class AssetService:
    @staticmethod
    def comprar_ativo_imobilizado(descricao, valor, entidade_fornecedor, data_aquisicao, conta_ativo_id, tipo_ativo, 
                                 num_parcelas=1, data_primeiro_vencimento=None, valor_juros=0):
        """
        Compra de Ativo a Prazo (Parcelada).
        """
        from datetime import date
        import calendar

        def add_months(sourcedate, months):
            month = sourcedate.month - 1 + months
            year = sourcedate.year + month // 12
            month = month % 12 + 1
            day = min(sourcedate.day, calendar.monthrange(year, month)[1])
            return date(year, month, day)

        # 1. Criar Registro de Ativo
        ativo = Ativo(
            descricao=descricao,
            tipo=tipo_ativo,
            valor_atual=valor,
            data_aquisicao=data_aquisicao,
            conta_contabil_id=conta_ativo_id
        )
        db.session.add(ativo)
        db.session.flush() 
        
        # 2. Configurações de Parcelas
        if not data_primeiro_vencimento:
            data_primeiro_vencimento = data_aquisicao
        
        num_parcelas = int(num_parcelas)
        valor_juros = Decimal(str(valor_juros))
        valor_total = valor + valor_juros
        valor_parcela = valor_total / num_parcelas

        # 3. Gerar Títulos (Parcelas)
        for i in range(1, num_parcelas + 1):
            vencimento = add_months(data_primeiro_vencimento, i - 1)
            desc_parcela = f"{descricao} ({i}/{num_parcelas})" if num_parcelas > 1 else descricao
            
            titulo = Titulo(
                entidade_id=entidade_fornecedor.id,
                descricao=f"Aquis. Ativo: {desc_parcela}",
                valor=valor_parcela,
                data_vencimento=vencimento,
                tipo=TipoTitulo.PAGAR.value,
                status=StatusTitulo.ABERTO.value,
                parcela_atual=i if num_parcelas > 1 else None,
                total_parcelas=num_parcelas if num_parcelas > 1 else None,
                ativo_id=ativo.id
            )
            db.session.add(titulo)
        
        return ativo

    @staticmethod
    def estornar_compra_ativo(ativo_id):
        """
        Estorna completamente a compra de um ativo.
        """
        ativo = db.session.get(Ativo, ativo_id)
        if not ativo:
            return False, "Ativo não encontrado."

        titulos_vinculados = Titulo.query.filter(
            (Titulo.ativo_id == ativo.id) | 
            (Titulo.descricao.like(f"Aquis. Ativo: {ativo.descricao}%"))
        ).all()
        
        for t in titulos_vinculados:
            if t.status == StatusTitulo.PAGO.value:
                return False, f"Não é permitido estornar ativos que possuam parcelas pagas ({t.descricao}). Estorne o pagamento primeiro."

        # 1. Remover Títulos
        for t in titulos_vinculados:
            if t.status == StatusTitulo.PAGO.value:
                FinancialService.estornar_titulo(t, motivo="Estorno de Aquisição de Ativo")
            
            TransacaoFinanceira.query.filter_by(titulo_id=t.id).delete()
            db.session.delete(t)

        # 2. Remover Ativo
        db.session.delete(ativo)
        
        return True, "Compra estornada com sucesso."

    @staticmethod
    def comprar_investimento(descricao, valor_unitario, quantidade, entidade_vendedor, data_aquisicao, conta_ativo_id, banco_ativo_id):
        """
        Compra de Investimento à Vista.
        """
        valor_total = Decimal(str(valor_unitario)) * Decimal(str(quantidade))
        
        ativo = Ativo(
            descricao=descricao,
            tipo=TipoAtivo.INVESTIMENTO.value,
            valor_atual=valor_total,
            data_aquisicao=data_aquisicao,
            conta_contabil_id=conta_ativo_id,
            quantidade=quantidade,
            valor_unitario=valor_unitario
        )
        db.session.add(ativo)
        db.session.flush()
        
        banco = db.session.get(Ativo, banco_ativo_id)
        if not banco or not banco.conta_contabil_id:
             raise ValueError("Banco inválido para liquidação à vista.")
             
        partidas = [
            {'conta_id': conta_ativo_id, 'tipo': 'D', 'valor': valor_total},
            {'conta_id': banco.conta_contabil_id, 'tipo': 'C', 'valor': valor_total}
        ]
        
        diario = AccountingService.criar_lancamento(
            historico=f"Compra Investimento: {descricao} ({quantidade} un x {valor_unitario})",
            data=data_aquisicao,
            partidas=partidas
        )
        
        transacao = TransacaoFinanceira(
            ativo_id=banco.id,
            tipo=TipoTransacao.AQUISICAO.value,
            valor=valor_total,
            data=data_aquisicao
        )
        db.session.add(transacao)
        db.session.flush()
        diario.transacao_id = transacao.id
        banco.valor_atual -= valor_total
        
        return ativo

    @staticmethod
    def recomprar_investimento(ativo_id, valor_unitario, quantidade, data_aquisicao, banco_ativo_id):
        """
        Aumenta a posição em um investimento já existente.
        """
        ativo = db.session.get(Ativo, ativo_id)
        if not ativo or ativo.tipo != TipoAtivo.INVESTIMENTO.value:
            raise ValueError("Ativo de investimento não encontrado.")
            
        valor_total = Decimal(str(valor_unitario)) * Decimal(str(quantidade))
        banco = db.session.get(Ativo, banco_ativo_id)
        
        nova_quantidade = ativo.quantidade + float(quantidade)
        novo_valor_total = ativo.valor_atual + valor_total
        ativo.valor_unitario = novo_valor_total / Decimal(str(nova_quantidade))
        ativo.quantidade = nova_quantidade
        ativo.valor_atual = novo_valor_total
        
        partidas = [
            {'conta_id': ativo.conta_contabil_id, 'tipo': 'D', 'valor': valor_total},
            {'conta_id': banco.conta_contabil_id, 'tipo': 'C', 'valor': valor_total}
        ]
        
        diario = AccountingService.criar_lancamento(
            historico=f"Recompra Investimento: {ativo.descricao} (+{quantidade} un)",
            data=data_aquisicao,
            partidas=partidas
        )
        
        transacao = TransacaoFinanceira(
            ativo_id=banco.id,
            tipo=TipoTransacao.AQUISICAO.value,
            valor=valor_total,
            data=data_aquisicao
        )
        db.session.add(transacao)
        db.session.flush()
        diario.transacao_id = transacao.id
        banco.valor_atual -= valor_total
        
        return ativo

    @staticmethod
    def vender_ativo(ativo_id, entidade_comprador, valor_venda, data_venda, num_parcelas=1, data_primeiro_vencimento=None):
        """
        Venda de Ativo Imobilizado (Veículo/Imóvel).
        """
        ativo = db.session.get(Ativo, ativo_id)
        if not ativo:
            raise ValueError("Ativo não encontrado.")
            
        num_parcelas = int(num_parcelas)
        valor_parcela = Decimal(str(valor_venda)) / num_parcelas
        dt_venc = data_primeiro_vencimento or data_venda
        
        from datetime import date
        import calendar
        def add_months_local(sourcedate, months):
            month = sourcedate.month - 1 + months
            year = sourcedate.year + month // 12
            month = month % 12 + 1
            day = min(sourcedate.day, calendar.monthrange(year, month)[1])
            return date(year, month, day)

        for i in range(1, num_parcelas + 1):
            vencimento = add_months_local(dt_venc, i - 1)
            desc_parcela = f"Venda Ativo: {ativo.descricao}" + (f" ({i}/{num_parcelas})" if num_parcelas > 1 else "")
            
            titulo = Titulo(
                entidade_id=entidade_comprador.id,
                descricao=desc_parcela,
                valor=valor_parcela,
                data_vencimento=vencimento,
                tipo=TipoTitulo.RECEBER.value,
                status=StatusTitulo.ABERTO.value,
                parcela_atual=i if num_parcelas > 1 else None,
                total_parcelas=num_parcelas if num_parcelas > 1 else None,
                ativo_id=ativo.id
            )
            db.session.add(titulo)
            
        conta_receber_id = entidade_comprador.conta_venda_id or entidade_comprador.conta_contabil_id
        if not conta_receber_id:
             raise ValueError("Comprador sem conta contábil vinculada.")

        partidas = [
            {'conta_id': conta_receber_id, 'tipo': 'D', 'valor': valor_venda},
            {'conta_id': ativo.conta_contabil_id, 'tipo': 'C', 'valor': ativo.valor_atual}
        ]
        
        diferenca = Decimal(str(valor_venda)) - ativo.valor_atual
        if diferenca > 0:
            # Tentar buscar conta por parâmetro
            conta_ganho = None
            conta_id = Configuracao.get_valor('conta_lucro_venda')
            if conta_id:
                c_param = db.session.get(ContaContabil, conta_id)
                if c_param and c_param.is_analitica:
                    conta_ganho = c_param
            
            # Fallback se não houver parâmetro válido
            if not conta_ganho:
                conta_ganho = ContaContabil.query.filter(ContaContabil.nome.like('%Ganho%Capital%')).first()
                if not conta_ganho:
                    conta_ganho = ContaContabil.query.filter(ContaContabil.tipo == TipoConta.RECEITA.value).first()
            
            partidas.append({'conta_id': conta_ganho.id, 'tipo': 'C', 'valor': diferenca})
            
        elif diferenca < 0:
            # Tentar buscar conta por parâmetro
            conta_perda = None
            conta_id = Configuracao.get_valor('conta_prejuizo_venda')
            if conta_id:
                c_param = db.session.get(ContaContabil, conta_id)
                if c_param and c_param.is_analitica:
                    conta_perda = c_param
            
            # Fallback se não houver parâmetro válido
            if not conta_perda:
                conta_perda = ContaContabil.query.filter(ContaContabil.nome.like('%Perda%Capital%')).first()
                if not conta_perda:
                    conta_perda = ContaContabil.query.filter(ContaContabil.tipo == TipoConta.DESPESA.value).first()
                    
            partidas.append({'conta_id': conta_perda.id, 'tipo': 'D', 'valor': abs(diferenca)})

        AccountingService.criar_lancamento(
            historico=f"Venda Ativo: {ativo.descricao}",
            data=data_venda,
            partidas=partidas
        )
        
        ativo.valor_atual = 0
        return ativo

    @staticmethod
    def vender_investimento(self, ativo_id, entidade_comprador, quantidade_venda, valor_unitario_venda, data_venda):
        # ... logic ...
        return ativo

class CreditCardService:
    @staticmethod
    def _obter_datas_ciclo(cartao, ano, mes):
        """Calcula as datas de fechamento e vencimento para uma competência específica."""
        import calendar
        from datetime import date
        
        # Data de fechamento
        ultimo_dia_mes = calendar.monthrange(ano, mes)[1]
        dia_f = min(cartao.dia_fechamento, ultimo_dia_mes)
        data_fechamento = date(ano, mes, dia_f)
        
        # Data de vencimento
        # Se o vencimento for menor que o fechamento, assume-se que é no mês seguinte?
        # Regra padrão: Vencimento na mesma competência da fatura (mês/ano)
        dia_v = min(cartao.dia_vencimento, ultimo_dia_mes)
        data_vencimento = date(ano, mes, dia_v)
        
        return data_fechamento, data_vencimento

    @staticmethod
    def obter_fatura_para_data(cartao, data_referencia):
        """
        Decide qual fatura recebe uma compra baseada na data e no dia de fechamento.
        """
        from datetime import date
        if isinstance(data_referencia, datetime):
            data_referencia = data_referencia.date()
            
        ano = data_referencia.year
        mes = data_referencia.month
        
        # Data de fechamento deste mês
        data_f_mes, _ = CreditCardService._obter_datas_ciclo(cartao, ano, mes)
        
        if data_referencia < data_f_mes:
            # Pertence à fatura do mês atual
            competencia = f"{ano}-{mes:02d}"
        else:
            # Pertence à fatura do mês seguinte
            proximo_mes = mes + 1
            proximo_ano = ano
            if proximo_mes > 12:
                proximo_mes = 1
                proximo_ano += 1
            competencia = f"{proximo_ano}-{proximo_mes:02d}"
            
        return CreditCardService.ensure_faturas(cartao, competencia)

    @staticmethod
    def ensure_faturas(cartao, competencia):
        """Garante que a fatura para a competência informada exista."""
        from .models import FaturaCartao
        
        fatura = FaturaCartao.query.filter_by(card_id=cartao.id, competencia=competencia).first()
        
        if not fatura:
            partes = competencia.split('-')
            ano, mes = int(partes[0]), int(partes[1])
            dt_f, dt_v = CreditCardService._obter_datas_ciclo(cartao, ano, mes)
            
            fatura = FaturaCartao(
                card_id=cartao.id,
                competencia=competencia,
                data_fechamento=dt_f,
                data_vencimento=dt_v,
                total=0.0,
                status='aberta',
                situacao_pagamento='em_aberto'
            )
            db.session.add(fatura)
            db.session.flush()
            
        return fatura

    @staticmethod
    def atualizar_total_fatura(fatura_id):
        """Recalcula o total de uma fatura baseado nas transações confirmadas."""
        from .models import FaturaCartao, TransacaoCartao
        from decimal import Decimal
        
        fatura = db.session.get(FaturaCartao, fatura_id)
        if not fatura: return
        
        total = db.session.query(db.func.sum(TransacaoCartao.valor))\
            .filter(TransacaoCartao.fatura_id == fatura.id)\
            .filter(TransacaoCartao.status == 'confirmada')\
            .scalar() or Decimal('0.00')
            
        fatura.total = total
        
        # Atualizar situação de pagamento
        if fatura.total_pago >= fatura.total and fatura.total > 0:
            fatura.situacao_pagamento = 'paga'
        elif fatura.total_pago > 0:
            fatura.situacao_pagamento = 'parcial'
        else:
            fatura.situacao_pagamento = 'em_aberto'
        
        # O ciclo (status) é alterado por data no obter_fatura_para_data
        # mas aqui podemos garantir consistência se necessário.
        # Por regra, não mexemos no status (ciclo) baseado em pagamento.
        
        db.session.flush()

    @staticmethod
    def registrar_compra(cartao, descricao, valor, categoria_id, data_compra, num_parcelas=1):
        """
        Registra uma compra no cartão de credito vinculada a uma ou mais faturas (se parcelado).
        """
        from .models import TransacaoCartao, TransacaoFinanceira, LivroDiario, PartidaDiario
        from decimal import Decimal
        import calendar
        from datetime import date

        def add_months(sourcedate, months):
            month = sourcedate.month - 1 + months
            year = sourcedate.year + month // 12
            month = month % 12 + 1
            day = min(sourcedate.day, calendar.monthrange(year, month)[1])
            return date(year, month, day)

        valor_total = Decimal(str(valor))
        num_parcelas = int(num_parcelas)
        
        # 1. VALIDAÇÃO DE LIMITE (Considerando Emergencial sobre o TOTAL da compra)
        folga_emergencial = Decimal('0')
        if cartao.limite_emergencial_ativo and cartao.perc_limite_emergencial > 0:
            folga_emergencial = cartao.limite_maximo_total - cartao.limite_total
        
        if valor_total > (cartao.limite_disponivel + folga_emergencial):
            if cartao.limite_emergencial_ativo and cartao.perc_limite_emergencial > 0:
                perc = int(cartao.perc_limite_emergencial * 100)
                raise ValueError(f"Limite insuficiente (considerando limite emergencial: {perc}%)")
            else:
                raise ValueError("Limite insuficiente.")

        # 2. Processar Parcelas
        valor_parcela = (valor_total / num_parcelas).quantize(Decimal("0.01"))
        valor_acumulado = Decimal('0.00')
        
        transacoes_geradas = []

        for i in range(1, num_parcelas + 1):
            # Ajuste de centavos na última parcela
            if i == num_parcelas:
                valor_atual_parcela = valor_total - valor_acumulado
            else:
                valor_atual_parcela = valor_parcela
                valor_acumulado += valor_atual_parcela

            # Data da parcela (mês a mês)
            data_parcela = data_compra if i == 1 else add_months(data_compra, i - 1)
            
            # Determinar Fatura da Parcela
            fatura = CreditCardService.obter_fatura_para_data(cartao, data_parcela)
            if fatura.status == 'fechada':
                # Se a fatura da 1ª parcela estiver fechada, pula para a próxima aberta
                # Mas para simplificar, vamos travar se a primeira estiver fechada.
                if i == 1:
                    raise ValueError(f"Não é possível lançar a 1ª parcela na fatura {fatura.competencia} pois o ciclo já está FECHADO.")
            
            desc_parcela = f"{descricao} ({i}/{num_parcelas})" if num_parcelas > 1 else descricao

            # 3. Contabilidade da Parcela
            partidas = [
                {'conta_id': categoria_id, 'tipo': 'D', 'valor': valor_atual_parcela},
                {'conta_id': cartao.conta_contabil_id, 'tipo': 'C', 'valor': valor_atual_parcela}
            ]
            
            diario = AccountingService.criar_lancamento(
                historico=f"Compra Cartão {cartao.nome}: {desc_parcela} (Fat: {fatura.competencia})",
                data=data_parcela,
                partidas=partidas
            )
            
            # 4. Registrar Transação no Cartão
            transacao_cartao = TransacaoCartao(
                card_id=cartao.id,
                fatura_id=fatura.id,
                competencia_calculada=fatura.competencia,
                data=data_parcela,
                descricao=desc_parcela,
                valor=valor_atual_parcela,
                categoria_id=categoria_id,
                status='confirmada'
            )
            db.session.add(transacao_cartao)
            db.session.flush()

            # 5. Link Contábil e Financeiro
            trans_fin = TransacaoFinanceira(
                ativo_id=None,
                tipo='CARTAO_COMPRA',
                valor=valor_atual_parcela,
                data=data_parcela
            )
            db.session.add(trans_fin)
            db.session.flush()
            
            diario.transacao_id = trans_fin.id
            transacao_cartao.transacao_financeira_id = trans_fin.id
            
            transacoes_geradas.append(transacao_cartao)
            CreditCardService.atualizar_total_fatura(fatura.id)

        # 6. Atualizar Limite (Pelo TOTAL da compra)
        if cartao.limite_disponivel is not None:
            cartao.limite_disponivel -= valor_total
            
        db.session.flush()
        
        return transacoes_geradas[0] # Retorna a primeira transação

    @staticmethod
    def realizar_pagamento_fatura(fatura_id, banco, valor_fatura, valor_encargos=0, conta_encargos_id=None, data_pagamento=None):
        """
        Registra o pagamento da fatura (principal + encargos) e recompõe limite.
        """
        from .models import FaturaCartao, PagamentoFaturaCartao, TransacaoFinanceira, TipoTransacao
        from decimal import Decimal
        
        fatura = db.session.get(FaturaCartao, fatura_id)
        if not fatura:
            raise ValueError("Fatura não encontrada.")
            
        cartao = fatura.cartao
        valor_fatura_dec = Decimal(str(valor_fatura))
        valor_encargos_dec = Decimal(str(valor_encargos or 0))
        valor_total_dec = valor_fatura_dec + valor_encargos_dec
        
        if not data_pagamento:
            data_pagamento = datetime.utcnow()
        
        # 1. Contabilidade - Principal
        partidas = [
            {'conta_id': cartao.conta_contabil_id, 'tipo': 'D', 'valor': valor_fatura_dec},
            {'conta_id': banco.conta_contabil_id, 'tipo': 'C', 'valor': valor_fatura_dec}
        ]
        
        # 2. Contabilidade - Encargos (se houver)
        if valor_encargos_dec > 0:
            if not conta_encargos_id:
                raise ValueError("Conta de despesa para encargos não informada.")
            
            partidas.append({'conta_id': conta_encargos_id, 'tipo': 'D', 'valor': valor_encargos_dec})
            partidas.append({'conta_id': banco.conta_contabil_id, 'tipo': 'C', 'valor': valor_encargos_dec})

        diario = AccountingService.criar_lancamento(
            historico=f"Pgto Fatura {fatura.competencia} (ID: {fatura.id}) - Cartão {cartao.nome}",
            data=data_pagamento,
            partidas=partidas
        )
        
        # 3. Registrar Transação Financeira (Extrato)
        transacao = TransacaoFinanceira(
            ativo_id=banco.id,
            tipo=TipoTransacao.PAGAMENTO.value,
            valor=valor_total_dec,
            data=data_pagamento
        )
        db.session.add(transacao)
        db.session.flush()
        diario.transacao_id = transacao.id
        
        # 4. Registrar Histórico de Pagamento
        pagto = PagamentoFaturaCartao(
            fatura_id=fatura.id,
            banco_id=banco.id,
            valor=valor_fatura_dec,
            valor_encargos=valor_encargos_dec,
            data_pagamento=data_pagamento,
            transacao_financeira_id=transacao.id
        )
        db.session.add(pagto)
        
        # 5. Atualizar Fatura e Cartão
        fatura.total_pago = (fatura.total_pago or Decimal('0')) + valor_fatura_dec
        fatura.data_pagamento_ultima = data_pagamento
        
        if fatura.total_pago >= fatura.total:
            fatura.situacao_pagamento = 'paga'
        else:
            fatura.situacao_pagamento = 'parcial'
            
        # Recompor Limite (Apenas pelo principal, capado pelo limite_maximo_total)
        if cartao.limite_disponivel is not None:
            cartao.limite_disponivel += valor_fatura_dec
            max_total = cartao.limite_maximo_total
            if cartao.limite_disponivel > max_total:
                cartao.limite_disponivel = max_total
        
        # Atualizar saldo do banco
        banco.valor_atual -= valor_total_dec
        
        return pagto

    @staticmethod
    def estornar_compra(transacao_id):
        """
        Estorna uma compra de cartão, devolve limite e atualiza fatura.
        """
        from .models import TransacaoCartao, TransacaoFinanceira
        from decimal import Decimal
        
        transacao = db.session.get(TransacaoCartao, transacao_id)
        if not transacao or transacao.status == 'estornada':
            return False, "Transação não encontrada ou já estornada."
        
        cartao = transacao.cartao
        fatura_id = transacao.fatura_id
        
        # 1. Contabilidade Inversa
        partidas = [
            {'conta_id': cartao.conta_contabil_id, 'tipo': 'D', 'valor': transacao.valor},
            {'conta_id': transacao.categoria_id, 'tipo': 'C', 'valor': transacao.valor}
        ]
        
        diario = AccountingService.criar_lancamento(
            historico=f"ESTORNO: Compra Cartão {cartao.nome} - {transacao.descricao}",
            data=datetime.utcnow(),
            partidas=partidas
        )
        
        # 2. Registrar Transação Financeira de Estorno
        trans_fin = TransacaoFinanceira(
            ativo_id=None,
            tipo='CARTAO_ESTORNO',
            valor=transacao.valor,
            data=datetime.utcnow()
        )
        db.session.add(trans_fin)
        db.session.flush()
        diario.transacao_id = trans_fin.id
        
        # 3. Devolver Limite (Capado pelo limite_maximo_total)
        if cartao.limite_disponivel is not None:
            cartao.limite_disponivel += Decimal(str(transacao.valor))
            max_total = cartao.limite_maximo_total
            if cartao.limite_disponivel > max_total:
                cartao.limite_disponivel = max_total
            
        # 4. Atualizar Transação e Fatura
        transacao.status = 'estornada'
        db.session.flush()
        CreditCardService.atualizar_total_fatura(fatura_id)
        
        return True, "Estorno realizado com sucesso!"
