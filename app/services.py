from . import db
from .models import LivroDiario, PartidaDiario, Titulo, TransacaoFinanceira, TipoTransacao, StatusTitulo, Ativo, ContaContabil, TipoConta, NaturezaConta, TipoTitulo, TipoAtivo
from datetime import datetime
from decimal import Decimal

class AccountingService:
    @staticmethod
    def criar_lancamento(historico, data, partidas):
        """
        Cria um lançamento no Livro Diário com validação de Partida Dobrada.
        partidas: Lista de dicionarios {'conta_id': int, 'tipo': 'D'/'C', 'valor': Decimal}
        """
        # 1. Validar Soma Zero (Débito == Crédito)
        total_debito = sum(p['valor'] for p in partidas if p['tipo'] == 'D')
        total_credito = sum(p['valor'] for p in partidas if p['tipo'] == 'C')

        if abs(total_debito - total_credito) > Decimal('0.01'):
            raise ValueError(f"O lançamento não balanceia! Débito: {total_debito}, Crédito: {total_credito}")

        # 2. Criar Lançamento Mestre
        diario = LivroDiario(historico=historico, data=data)
        db.session.add(diario)
        db.session.flush() # Gerar ID do diário

        # 3. Criar Partidas
        for p in partidas:
            # Validar se conta é analítica
            conta = db.session.get(ContaContabil, p['conta_id'])
            if not conta:
                raise ValueError(f"Conta ID {p['conta_id']} não encontrada.")
            # TODO: Idealmente validar se conta.is_analitica, mas requer query extra ou eager loading

            partida = PartidaDiario(
                diario_id=diario.id, 
                conta_id=p['conta_id'], 
                tipo=p['tipo'], 
                valor=p['valor']
            )
            db.session.add(partida)
        
        return diario

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
        Se Pagar: D: Fornecedor / C: Banco
        Se Receber: D: Banco / C: Cliente
        """
        if titulo.status == StatusTitulo.PAGO:
            raise ValueError("Título já está pago.")

        # Buscar o ativo banco para pegar sua conta contábil
        banco = db.session.get(Ativo, conta_banco_id)
        if not banco or not banco.conta_contabil_id:
            raise ValueError("Banco inválido ou sem conta contábil.")

        # 1. Definir Contas para Lançamento Único (Regime de Caixa)
        # Prioridade 1: Se o título estiver vinculado a um ativo, usar a conta contábil do ativo (Patrimonial)
        if titulo.ativo_id and titulo.ativo and titulo.ativo.conta_contabil_id:
            conta_categoria_id = titulo.ativo.conta_contabil_id
        else:
            # Prioridade 2: Contrapartida (Categoria da Entidade - Resultado/Despesa/Receita)
            conta_categoria_id = titulo.entidade.conta_resultado_id
            if not conta_categoria_id:
                if titulo.tipo == 'Pagar' or titulo.tipo == TipoTitulo.PAGAR.value:
                    conta_categoria_id = titulo.entidade.conta_compra_id
                else:
                    conta_categoria_id = titulo.entidade.conta_venda_id

        if not conta_categoria_id:
            raise ValueError(f"Entidade '{titulo.entidade.nome}' não possui conta de categoria (Venda/Receita ou Compra/Despesa) configurada.")

        # Lógica de Partidas
        partidas = []
        tipo_transacao = None

        if titulo.tipo == 'Pagar' or titulo.tipo == TipoTitulo.PAGAR.value:
            # PAGAMENTO: D: Categoria (Despesa), C: Banco
            partidas = [
                {'conta_id': conta_categoria_id, 'tipo': 'D', 'valor': titulo.valor},
                {'conta_id': banco.conta_contabil_id, 'tipo': 'C', 'valor': titulo.valor}
            ]
            tipo_transacao = TipoTransacao.PAGAMENTO.value
            banco.valor_atual -= titulo.valor
        else: # RECEBIMENTO
            # RECEBIMENTO: D: Banco, C: Categoria (Receita)
            partidas = [
                {'conta_id': banco.conta_contabil_id, 'tipo': 'D', 'valor': titulo.valor},
                {'conta_id': conta_categoria_id, 'tipo': 'C', 'valor': titulo.valor}
            ]
            tipo_transacao = TipoTransacao.RECEBIMENTO.value
            banco.valor_atual += titulo.valor

        # 2. Atualizar Título
        titulo.status = StatusTitulo.PAGO.value
        
        # 2. Criar Transação Financeira
        transacao = TransacaoFinanceira(
            titulo_id=titulo.id,
            ativo_id=banco.id,
            tipo=tipo_transacao, # Já convertida para string no if/else acima
            valor=titulo.valor,
            data=data_pagamento
        )
        db.session.add(transacao)
        db.session.flush()

        # 3. Contabilidade
        diario = AccountingService.criar_lancamento(
            historico=f"Liq. Titulo {titulo.id} - {titulo.descricao}",
            data=data_pagamento,
            partidas=partidas
        )
        diario.transacao_id = transacao.id # Vínculo Reverso
        
        return transacao

    @staticmethod
    def estornar_titulo(titulo, motivo="Cancelamento"):
        """
        Anula contabilmente um título e sua liquidação (se houver).
        Usa lançamentos inversos para manter a trilha de auditoria.
        """
        if titulo.status == StatusTitulo.CANCELADO.value:
            raise ValueError("Título já está cancelado.")

        # 1. Se estiver Pago, estornar a Liquidação primeiro
        if titulo.status == StatusTitulo.PAGO.value:
            # Buscar a última transação de liquidação
            transacao = TransacaoFinanceira.query.filter_by(titulo_id=titulo.id).order_by(TransacaoFinanceira.data.desc()).first()
            if transacao and transacao.ativo:
                banco = transacao.ativo
                # 1.1 Resolver Conta da Entidade para estorno da Liquidação
                conta_entidade_id = titulo.entidade.conta_contabil_id
                if not conta_entidade_id:
                    if titulo.tipo == 'Pagar' or titulo.tipo == TipoTitulo.PAGAR.value:
                        c_padrao = ContaContabil.query.filter_by(codigo='2.3.01').first()
                        if c_padrao: conta_entidade_id = c_padrao.id
                    else:
                        c_padrao = ContaContabil.query.filter_by(codigo='1.5.01').first()
                        if c_padrao: conta_entidade_id = c_padrao.id
                
                if titulo.tipo == 'Pagar' or titulo.tipo == TipoTitulo.PAGAR.value:
                    # Inverter Liq Pagar (D: Fornecedor / C: Banco)
                    # Estorno: D: Banco / C: Fornecedor
                    partidas_estorno_liq = [
                        {'conta_id': banco.conta_contabil_id, 'tipo': 'D', 'valor': titulo.valor},
                        {'conta_id': conta_entidade_id, 'tipo': 'C', 'valor': titulo.valor}
                    ]
                    # Reverter Saldo do Banco (Aumentar)
                    banco.valor_atual += titulo.valor
                else: # RECEBER
                    # Inverter Liq Receber (D: Banco / C: Cliente)
                    # Estorno: D: Cliente / C: Banco
                    partidas_estorno_liq = [
                        {'conta_id': conta_entidade_id, 'tipo': 'D', 'valor': titulo.valor},
                        {'conta_id': banco.conta_contabil_id, 'tipo': 'C', 'valor': titulo.valor}
                    ]
                    # Reverter Saldo do Banco (Diminuir)
                    banco.valor_atual -= titulo.valor
                
                AccountingService.criar_lancamento(
                    historico=f"ESTORNO LIQ: {titulo.descricao} (ID: {titulo.id})",
                    data=datetime.utcnow(),
                    partidas=partidas_estorno_liq
                )

        # 2. Inativar o Título
        titulo.status = StatusTitulo.CANCELADO.value
        
        return True

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
        # diário.transacao_id será vinculado automaticamente se configurado ou faremos após o commit da sessão
        # Por enquanto, vamos vincular o objeto e o SQLAlchemy cuidará do ID no commit
        diario.transacao_id = transacao.id # Se transacao.id for None aqui, será resolvido no commit

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
        D: Banco Destino
        C: Banco Origem
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
        
        # Transação Financeira
        # Opcional: Podemos criar duas transações (uma de saída e uma de entrada) ou uma única representando a transferência
        # Simplificação: Uma transação de Transferência vinculada a conta de origem (banco que saiu o dinheiro)
        # Para rastrear o destino, precisaríamos de outro campo ou interpretar o lançamento contábil.
        # Vamos assumir que Ativo ID aqui é a origem.
        
        # Tentar achar o Ativo associado à conta contábil para preencher ativo_id (se houver)
        # (Já buscamos acima)
        
        transacao = TransacaoFinanceira(
            titulo_id=None,
            ativo_id=ativo_origem.id if ativo_origem else None,
            tipo=TipoTransacao.TRANSFERENCIA.value,
            valor=valor,
            data=data
        )
        db.session.add(transacao)
        db.session.flush() # Garantir ID
        
        diario.transacao_id = transacao.id
        
        return transacao

    @staticmethod
    def realizar_transferencia_generica(conta_debito_id, conta_credito_id, valor, historico, data):
        """
        Realiza um lançamento contábil simples entre duas contas.
        Não gera TransacaoFinanceira complexa, apenas registro contábil e talvez uma transação 'OUTROS'.
        Útil para Saldo Inicial, Ajustes, etc.
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
        D: Ativo Fixo (Imobilizado) -> Valor Principal
        D: Despesas Financeiras (Juros) -> Valor Juros
        C: Fornecedor (Passivo) -> Valor Total
        """
        from datetime import date
        import calendar

        def add_months(sourcedate, months):
            month = sourcedate.month - 1 + months
            year = sourcedate.year + month // 12
            month = month % 12 + 1
            day = min(sourcedate.day, calendar.monthrange(year, month)[1])
            return date(year, month, day)

        # 1. Criar Registro de Ativo (Fixo) -> Somente Valor Principal
        ativo = Ativo(
            descricao=descricao,
            tipo=tipo_ativo,
            valor_atual=valor,
            data_aquisicao=data_aquisicao,
            conta_contabil_id=conta_ativo_id
        )
        db.session.add(ativo)
        db.session.flush() # Gerar ID do ativo
        
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

        # 4. Contabilidade (Regime de Caixa: Não há lançamento na provisão do Ativo se parcelado)
        # O lançamento ocorrerá apenas na liquidação de cada título.
        
        return ativo

    @staticmethod
    def estornar_compra_ativo(ativo_id):
        """
        Estorna completamente a compra de um ativo.
        Remove o ativo, os títulos e estorna a contabilidade via lançamentos inversos.
        """
        ativo = db.session.get(Ativo, ativo_id)
        if not ativo:
            return False, "Ativo não encontrado."

        # VERIFICAÇÃO DE SEGURANÇA: Não permitir estorno se houver parcelas pagas
        # Buscamos títulos vinculados (ID ou Descrição como fallback)
        titulos_vinculados = Titulo.query.filter(
            (Titulo.ativo_id == ativo.id) | 
            (Titulo.descricao.like(f"Aquis. Ativo: {ativo.descricao}%"))
        ).all()
        
        for t in titulos_vinculados:
            if t.status == StatusTitulo.PAGO.value:
                return False, f"Não é permitido estornar ativos que possuam parcelas pagas ({t.descricao}). Estorne o pagamento primeiro."

        # 1. Remover Títulos vinculados e suas liquidações
        titulos = Titulo.query.filter_by(ativo_id=ativo.id).all()
        
        if not titulos:
            titulos = Titulo.query.filter(Titulo.descricao.like(f"Aquis. Ativo: {ativo.descricao}%")).all()
        
        for t in titulos:
            # Estornar contabilidade se estiver pago (Regime de Caixa)
            if t.status == StatusTitulo.PAGO.value:
                FinancialService.estornar_titulo(t, motivo="Estorno de Aquisição de Ativo")
            
            # Remover transações de extrato vinculadas à liquidação
            TransacaoFinanceira.query.filter_by(titulo_id=t.id).delete()
            db.session.delete(t)

        # 2. Remover Ativo
        db.session.delete(ativo)
        
        return True, "Compra estornada com sucesso."
    @staticmethod
    def comprar_investimento(descricao, valor_unitario, quantidade, entidade_vendedor, data_aquisicao, conta_ativo_id, banco_ativo_id):
        """
        Compra de Investimento à Vista.
        D: Ativo Investimento (Balanço)
        C: Ativo Banco (Balanço)
        """
        valor_total = Decimal(str(valor_unitario)) * Decimal(str(quantidade))
        
        # 1. Criar Registro de Ativo
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
        
        # 2. Buscar Banco para baixa imediata
        banco = db.session.get(Ativo, banco_ativo_id)
        if not banco or not banco.conta_contabil_id:
             raise ValueError("Banco inválido para liquidação à vista.")
             
        # 3. Contabilidade (Direta entre contas patrimoniais do Ativo)
        partidas = [
            {'conta_id': conta_ativo_id, 'tipo': 'D', 'valor': valor_total},
            {'conta_id': banco.conta_contabil_id, 'tipo': 'C', 'valor': valor_total}
        ]
        
        diario = AccountingService.criar_lancamento(
            historico=f"Compra Investimento: {descricao} ({quantidade} un x {valor_unitario})",
            data=data_aquisicao,
            partidas=partidas
        )
        
        # 4. Transação Financeira
        transacao = TransacaoFinanceira(
            ativo_id=banco.id, # Banco que saiu o dinheiro
            tipo=TipoTransacao.AQUISICAO.value,
            valor=valor_total,
            data=data_aquisicao
        )
        db.session.add(transacao)
        db.session.flush()
        diario.transacao_id = transacao.id
        
        # Atualizar saldo do banco
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
        
        # Atualizar Ativo (Média ponderada ou apenas soma?)
        # O usuário pediu: "não permitir a toca de valor e quantidade de um ativo já liquidado, ele será somado"
        # Entendo que somamos quantidade e atualizamos o valor_atual
        nova_quantidade = ativo.quantidade + float(quantidade)
        novo_valor_total = ativo.valor_atual + valor_total
        # Novo preço unitário médio
        ativo.valor_unitario = novo_valor_total / Decimal(str(nova_quantidade))
        ativo.quantidade = nova_quantidade
        ativo.valor_atual = novo_valor_total
        
        # Contabilidade e Transação (Igual à compra)
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
        Gera Títulos a Receber.
        Contabilidade:
        D: Cliente (Receber) -> Valor Venda
        C: Ativo (Baixa) -> Valor de Custo/Atual (Aqui simplificaremos baixando o total)
        # TODO: Ganho/Perda de Capital se valor_venda != valor_atual
        """
        ativo = db.session.get(Ativo, ativo_id)
        if not ativo:
            raise ValueError("Ativo não encontrado.")
            
        # 1. Gerar Títulos a Receber
        num_parcelas = int(num_parcelas)
        valor_parcela = Decimal(str(valor_venda)) / num_parcelas
        dt_venc = data_primeiro_vencimento or data_venda
        
        from .services import FinancialService # Import local para evitar circular se necessário
        
        for i in range(1, num_parcelas + 1):
            from datetime import date
            import calendar
            def add_months(sourcedate, months):
                month = sourcedate.month - 1 + months
                year = sourcedate.year + month // 12
                month = month % 12 + 1
                day = min(sourcedate.day, calendar.monthrange(year, month)[1])
                return date(year, month, day)
            
            vencimento = add_months(dt_venc, i - 1)
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
            
        # 2. Contabilidade de Baixa do Ativo
        # Simplificação: Baixa pelo valor atual. Ganho/Perda tratado como diferença para Receita/Despesa.
        # D: Contas a Receber (Cliente ou Conta Venda específica) -> Valor Venda
        # C: Ativo (Bem) -> Valor do Bem
        # Diferença -> Ganho ou Perda de Capital
        
        conta_receber_id = entidade_comprador.conta_venda_id or entidade_comprador.conta_contabil_id
        if not conta_receber_id:
             raise ValueError("Comprador sem conta contábil vinculada.")

        partidas = [
            {'conta_id': conta_receber_id, 'tipo': 'D', 'valor': valor_venda},
            {'conta_id': ativo.conta_contabil_id, 'tipo': 'C', 'valor': ativo.valor_atual}
        ]
        
        diferenca = valor_venda - ativo.valor_atual
        if diferenca > 0:
            # Ganho de Capital (Receita)
            conta_ganho = ContaContabil.query.filter(ContaContabil.nome.like('%Ganho%Capital%')).first()
            if not conta_ganho:
                conta_ganho = ContaContabil.query.filter(ContaContabil.tipo == TipoConta.RECEITA.value).first()
            partidas.append({'conta_id': conta_ganho.id, 'tipo': 'C', 'valor': diferenca})
        elif diferenca < 0:
            # Perda de Capital (Despesa)
            conta_perda = ContaContabil.query.filter(ContaContabil.nome.like('%Perda%Capital%')).first()
            if not conta_perda:
                conta_perda = ContaContabil.query.filter(ContaContabil.tipo == TipoConta.DESPESA.value).first()
            partidas.append({'conta_id': conta_perda.id, 'tipo': 'D', 'valor': abs(diferenca)})

        AccountingService.criar_lancamento(
            historico=f"Venda Ativo: {ativo.descricao}",
            data=data_venda,
            partidas=partidas
        )
        
        # 3. Marcar ativo como vendido (ou apenas reduzir valor se for parcial, mas aqui imobilizado é total)
        ativo.valor_atual = 0
        # Opcional: deletar ativo ou marcar status
        
        return ativo

    @staticmethod
    def vender_investimento(ativo_id, entidade_comprador, quantidade_venda, valor_unitario_venda, data_venda):
        """
        Venda parcial ou total de investimento. Somente à vista para simplificar conforme pedido? 
        "gerar um título financeiro como todos os outros para liquidar" -> Indica que pode ser parcelado ou a prazo.
        """
        ativo = db.session.get(Ativo, ativo_id)
        if not ativo or ativo.tipo != TipoAtivo.INVESTIMENTO.value:
            raise ValueError("Investimento não encontrado.")
            
        if float(quantidade_venda) > ativo.quantidade:
            raise ValueError("Quantidade insuficiente para venda.")
            
        valor_venda_total = Decimal(str(valor_unitario_venda)) * Decimal(str(quantidade_venda))
        valor_custo_total = ativo.valor_unitario * Decimal(str(quantidade_venda))
        
        # 1. Criar Título a Receber (Venda à vista = 1 parcela vencendo hoje)
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
        
        # D: Contas a Receber (Cliente ou Conta Venda específica) -> Valor Venda
        # C: Ativo Investimento -> Valor de Custo
        # C/D: Ganho/Perda -> Diferença
        
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
        
        # 3. Atualizar Ativo
        ativo.quantidade -= float(quantidade_venda)
        ativo.valor_atual -= valor_custo_total
        
        return ativo
