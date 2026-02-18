from . import db
from .models import LivroDiario, PartidaDiario, Titulo, TransacaoFinanceira, TipoTransacao, StatusTitulo, Ativo, ContaContabil, TipoConta, NaturezaConta, TipoTitulo, TipoAtivo
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
    def registrar_liquidacao_titulo(titulo, banco, data_pagamento):
        """
        Inteligência de Domínio: Decide as partidas contábeis para a liquidação de um título.
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
        partidas = []
        if titulo.tipo == 'Pagar' or titulo.tipo == TipoTitulo.PAGAR.value:
            # PAGAMENTO: D: Categoria (Despesa), C: Banco
            partidas = [
                {'conta_id': conta_category_id, 'tipo': 'D', 'valor': titulo.valor},
                {'conta_id': banco.conta_contabil_id, 'tipo': 'C', 'valor': titulo.valor}
            ]
        else: # RECEBIMENTO
            # RECEBIMENTO: D: Banco, C: Categoria (Receita)
            partidas = [
                {'conta_id': banco.conta_contabil_id, 'tipo': 'D', 'valor': titulo.valor},
                {'conta_id': conta_category_id, 'tipo': 'C', 'valor': titulo.valor}
            ]

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
    def liquidar_titulo(titulo, conta_banco_id, data_pagamento):
        """
        Liquida um título utilizando saldo de um Banco (Ativo).
        A inteligência das partidas contábeis foi movida para o AccountingService.
        """
        if titulo.status == StatusTitulo.PAGO.value:
            raise ValueError("Título já está pago.")

        # Buscar o ativo banco
        banco = db.session.get(Ativo, conta_banco_id)
        if not banco or not banco.conta_contabil_id:
            raise ValueError("Banco inválido ou sem conta contábil.")

        # 1. Atualizar Saldo e Status (Financeiro)
        if titulo.tipo == 'Pagar' or titulo.tipo == TipoTitulo.PAGAR.value:
            banco.valor_atual -= titulo.valor
            tipo_transacao = TipoTransacao.PAGAMENTO.value
        else:
            banco.valor_atual += titulo.valor
            tipo_transacao = TipoTransacao.RECEBIMENTO.value

        titulo.status = StatusTitulo.PAGO.value
        
        # 2. Criar Transação Financeira (Extrato)
        transacao = TransacaoFinanceira(
            titulo_id=titulo.id,
            ativo_id=banco.id,
            tipo=tipo_transacao,
            valor=titulo.valor,
            data=data_pagamento
        )
        db.session.add(transacao)
        db.session.flush()

        # 3. Gerar Contabilidade (Domínio Contábil)
        diario = AccountingService.registrar_liquidacao_titulo(titulo, banco, data_pagamento)
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
            final_conta_contra_id = int(conta_pl_id)
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
            conta_ganho = ContaContabil.query.filter(ContaContabil.nome.like('%Ganho%Capital%')).first()
            if not conta_ganho:
                conta_ganho = ContaContabil.query.filter(ContaContabil.tipo == TipoConta.RECEITA.value).first()
            partidas.append({'conta_id': conta_ganho.id, 'tipo': 'C', 'valor': diferenca})
        elif diferenca < 0:
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
    def vender_investimento(ativo_id, entidade_comprador, quantidade_venda, valor_unitario_venda, data_venda):
        """
        Venda parcial ou total de investimento.
        """
        ativo = db.session.get(Ativo, ativo_id)
        if not ativo or ativo.tipo != TipoAtivo.INVESTIMENTO.value:
            raise ValueError("Investimento não encontrado.")
            
        if float(quantidade_venda) > ativo.quantidade:
            raise ValueError("Quantidade insuficiente para venda.")
            
        valor_venda_total = Decimal(str(valor_unitario_venda)) * Decimal(str(quantidade_venda))
        valor_custo_total = ativo.valor_unitario * Decimal(str(quantidade_venda))
        
        titulo = Titulo(
            entidade_id=entidade_comprador.id,
            descricao=f"Venda Investimento: {ativo.descricao} ({quantidade_venda} un)",
            valor=valor_venda_total,
            data_vencimento=data_venda,
            tipo=TipoTitulo.RECEBER.value,
            status=StatusTitulo.ABERTO.value,
            ativo_id=ativo.id
        )
        db.session.add(titulo)
        
        conta_receber_id = entidade_comprador.conta_venda_id or entidade_comprador.conta_contabil_id
        if not conta_receber_id:
             raise ValueError("Comprador sem conta contábil vinculada.")

        partidas = [
            {'conta_id': conta_receber_id, 'tipo': 'D', 'valor': valor_venda_total},
            {'conta_id': ativo.conta_contabil_id, 'tipo': 'C', 'valor': valor_custo_total}
        ]
        
        diferenca = valor_venda_total - valor_custo_total
        if diferenca > 0:
            conta_ganho = ContaContabil.query.filter(ContaContabil.nome.like('%Ganho%Capital%')).first()
            if not conta_ganho:
                conta_ganho = ContaContabil.query.filter(ContaContabil.tipo == TipoConta.RECEITA.value).first()
            partidas.append({'conta_id': conta_ganho.id, 'tipo': 'C', 'valor': diferenca})
        elif diferenca < 0:
            conta_perda = ContaContabil.query.filter(ContaContabil.nome.like('%Perda%Capital%')).first()
            if not conta_perda:
                conta_perda = ContaContabil.query.filter(ContaContabil.tipo == TipoConta.DESPESA.value).first()
            partidas.append({'conta_id': conta_perda.id, 'tipo': 'D', 'valor': abs(diferenca)})

        AccountingService.criar_lancamento(
            historico=f"Venda Investimento: {ativo.descricao} ({quantidade_venda} un)",
            data=data_venda,
            partidas=partidas
        )
        
        ativo.quantidade -= float(quantidade_venda)
        ativo.valor_atual -= valor_custo_total
        
        return ativo
