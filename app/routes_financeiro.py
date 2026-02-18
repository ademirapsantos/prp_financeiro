from flask import Blueprint, render_template, request, redirect, url_for, flash
from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy import func
from .models import Titulo, Ativo, ContaContabil, TipoConta, TipoTitulo, StatusTitulo, PartidaDiario, LivroDiario, Entidade, TipoEntidade, TipoAtivo, db
from .services import FinancialService

financeiro_bp = Blueprint('financeiro', __name__, url_prefix='/financeiro')

from sqlalchemy.orm import joinedload

@financeiro_bp.route('/titulos')
def titulos():
    # Capturar filtros
    data_inicio_str = request.args.get('data_inicio')
    data_fim_str = request.args.get('data_fim')
    tipo_filtro = request.args.get('tipo')
    entidade_id = request.args.get('entidade_id')
    status_filtro = request.args.get('status')
    active_tab = request.args.get('tab', 'pendentes')

    # Capturar página atual
    page = request.args.get('page', 1, type=int)
    per_page = 50

    # Query base para os totais (sem paginação, mas com filtros)
    total_query = db.session.query(
        func.sum(Titulo.valor).filter(Titulo.tipo == TipoTitulo.RECEBER.value, Titulo.status == StatusTitulo.ABERTO.value).label('receber'),
        func.sum(Titulo.valor).filter(Titulo.tipo == TipoTitulo.PAGAR.value, Titulo.status == StatusTitulo.ABERTO.value).label('pagar')
    )

    query = Titulo.query.options(joinedload(Titulo.entidade), joinedload(Titulo.ativo))

    if data_inicio_str:
        dt_ini = datetime.strptime(data_inicio_str, '%Y-%m-%d').date()
        query = query.filter(Titulo.data_vencimento >= dt_ini)
        total_query = total_query.filter(Titulo.data_vencimento >= dt_ini)
    if data_fim_str:
        dt_fim = datetime.strptime(data_fim_str, '%Y-%m-%d').date()
        query = query.filter(Titulo.data_vencimento <= dt_fim)
        total_query = total_query.filter(Titulo.data_vencimento <= dt_fim)
    if tipo_filtro:
        query = query.filter(Titulo.tipo == tipo_filtro)
        total_query = total_query.filter(Titulo.tipo == tipo_filtro)
    if entidade_id:
        ent_id = int(entidade_id)
        query = query.filter(Titulo.entidade_id == ent_id)
        total_query = total_query.filter(Titulo.entidade_id == ent_id)
    
    # Lógica de Abas vs Status
    if status_filtro:
        query = query.filter(Titulo.status == status_filtro)
        total_query = total_query.filter(Titulo.status == status_filtro)
        if status_filtro == StatusTitulo.PAGO.value:
            active_tab = 'pagas'
        elif status_filtro == StatusTitulo.ABERTO.value:
            active_tab = 'pendentes'
    else:
        if active_tab == 'pagas':
            query = query.filter(Titulo.status == StatusTitulo.PAGO.value)
            total_query = total_query.filter(Titulo.status == StatusTitulo.PAGO.value)
        else:
            query = query.filter(Titulo.status == StatusTitulo.ABERTO.value)
            total_query = total_query.filter(Titulo.status == StatusTitulo.ABERTO.value)

    # Executar query de totais
    res_totais = total_query.first()
    total_receber = res_totais.receber or 0
    total_pagar = res_totais.pagar or 0

    # Paginação
    pagination = query.order_by(Titulo.data_vencimento).paginate(page=page, per_page=per_page, error_out=False)
    lista_titulos = pagination.items
    
    # Lista de entidades otimizada para o filtro (Apenas ID e Nome)
    entidades = db.session.query(Entidade.id, Entidade.nome).order_by(Entidade.nome).all()
    
    hoje = datetime.utcnow().date()
    data_limite_estorno = hoje - timedelta(days=60)
    
    # Sanitizar filtros para os links das abas e paginação
    filtros_limpos = {k: v for k, v in request.args.items() if k not in ['tab', 'status', 'page']}
    
    return render_template('financeiro/titulos.html', 
                         titulos=lista_titulos, 
                         pagination=pagination,
                         total_receber=total_receber, 
                         total_pagar=total_pagar,
                         entidades=entidades,
                         filtros=filtros_limpos,
                         data_limite_estorno=data_limite_estorno,
                         active_tab=active_tab)

@financeiro_bp.route('/liquidar/<int:titulo_id>', methods=['GET', 'POST'])
def liquidar_titulo_route(titulo_id):
    titulo = db.session.get(Titulo, titulo_id)
    if not titulo:
        flash("Título não encontrado.", "error")
        return redirect(url_for('financeiro.titulos'))

    if request.method == 'POST':
        try:
            banco_id = int(request.form.get('banco_id'))
            data_pagamento = datetime.strptime(request.form.get('data_pagamento'), '%Y-%m-%d')
            
            FinancialService.liquidar_titulo(titulo, banco_id, data_pagamento)
            db.session.commit()
            flash(f"Título '{titulo.descricao}' liquidado com sucesso!", "success")
            return redirect(url_for('financeiro.titulos'))
        except Exception as e:
            db.session.rollback()
            flash(f"Erro ao liquidar título: {str(e)}", "error")

    # GET: Mostrar formulário
    bancos = Ativo.query.filter_by(tipo='Banco').all()
    if not bancos:
        flash("Nenhuma conta bancária/caixa encontrada. Cadastre um banco antes de liquidar.", "warning")
        return redirect(url_for('financeiro.bancos'))
        
    hoje = datetime.utcnow().strftime('%Y-%m-%d')
    return render_template('financeiro/liquidar_form.html', titulo=titulo, bancos=bancos, hoje=hoje)

@financeiro_bp.route('/transferencia', methods=['GET', 'POST'])
def transferencia():
    if request.method == 'POST':
        try:
            conta_origem_id = int(request.form.get('conta_origem'))
            conta_destino_id = int(request.form.get('conta_destino'))
            valor = Decimal(request.form.get('valor'))
            data_str = request.form.get('data')
            data = datetime.strptime(data_str, '%Y-%m-%d')
            descricao = request.form.get('descricao')
            
            FinancialService.realizar_transferencia(
                conta_origem_id, 
                conta_destino_id, 
                valor, 
                data, 
                descricao
            )
            db.session.commit()
            flash('Transferência realizada com sucesso!', 'success')
            return redirect(url_for('main.dashboard'))
            
        except Exception as e:
            db.session.rollback()
            flash(f"Erro na transferência: {str(e)}", "error")
            return redirect(url_for('financeiro.transferencia'))

    # Carregar contas do Ativo (Bancos/Caixa)
    contas = ContaContabil.query.filter(ContaContabil.tipo == TipoConta.ATIVO.value).all()
    contas_selecionaveis = [c for c in contas if c.is_analitica]
    
    hoje_str = datetime.utcnow().strftime('%Y-%m-%d')
    
    return render_template('financeiro/transferencia.html', contas=contas_selecionaveis, hoje_str=hoje_str)

@financeiro_bp.route('/fluxo-caixa')
def fluxo_caixa():
    # 1. Saldo Atual (Disponível)
    contas_disponivel = db.session.query(ContaContabil.id).filter(ContaContabil.codigo.like('1.1%')).subquery()
    
    stmt = db.session.query(
        func.sum(PartidaDiario.valor).filter(PartidaDiario.tipo == 'D').label('debitos'),
        func.sum(PartidaDiario.valor).filter(PartidaDiario.tipo == 'C').label('creditos')
    ).filter(PartidaDiario.conta_id.in_(contas_disponivel))
    
    res = stmt.first()
    saldo_atual = (res.debitos or 0) - (res.creditos or 0) if res else 0

    # 2. Previsões (Títulos em Aberto)
    hoje = datetime.utcnow().date()
    
    receber_total = db.session.query(func.sum(Titulo.valor)).filter(
        Titulo.tipo == TipoTitulo.RECEBER.value,
        Titulo.status == StatusTitulo.ABERTO.value
    ).scalar() or 0
    
    pagar_total = db.session.query(func.sum(Titulo.valor)).filter(
        Titulo.tipo == TipoTitulo.PAGAR.value,
        Titulo.status == StatusTitulo.ABERTO.value
    ).scalar() or 0
    
    saldo_projetado = saldo_atual + receber_total - pagar_total
    
    # 3. Extrato Recente (Simples por enquanto, pegando do Diário de Bancos seria o ideal)
    # Vamos listar as últimas transferências e liquidações
    # Isso requer query na TransacaoFinanceira
    # TODO: Implementar lista de transações

    return render_template('financeiro/fluxo_caixa.html',
                         saldo_atual=saldo_atual,
                         receber=receber_total,
                         pagar=pagar_total,
                         saldo_projetado=saldo_projetado)

@financeiro_bp.route('/bancos')
def bancos():
    # Listar ativos do tipo Banco ou Carteira
    bancos = Ativo.query.filter(Ativo.tipo.in_(['Banco', 'Carteira'])).all()
    # Para cada banco, podemos tentar buscar o saldo atual da conta contábil vinculada
    dados_bancos = []
    for b in bancos:
        saldo = 0
        if b.conta_contabil_id:
            # Calcular saldo (D - C)
            try:
                stmt = db.session.query(
                    func.sum(PartidaDiario.valor).filter(PartidaDiario.tipo == 'D').label('debitos'),
                    func.sum(PartidaDiario.valor).filter(PartidaDiario.tipo == 'C').label('creditos')
                ).filter(PartidaDiario.conta_id == b.conta_contabil_id)
                res = stmt.first()
                if res:
                    saldo = (res.debitos or 0) - (res.creditos or 0)
            except Exception as e:
                print(f"Erro ao calcular saldo banco {b.descricao}: {e}")
        
        dados_bancos.append({
            'id': b.id,
            'nome': b.descricao,
            'codigo': b.conta_contabil.codigo if b.conta_contabil else 'N/A',
            'saldo': saldo,
            'banco_obj': b
        })
        
    # Buscar contas contábeis analíticas do Ativo para o modal de novo banco
    contas_banco = ContaContabil.query.filter(
        ContaContabil.tipo == TipoConta.ATIVO.value
    ).all()
    # Filtrar apenas analíticas (sem subcontas)
    contas_analiticas = [c for c in contas_banco if c.is_analitica]
    
    return render_template('financeiro/bancos.html', 
                          bancos=dados_bancos, 
                          contas_contabeis=contas_analiticas)

@financeiro_bp.route('/bancos/novo', methods=['GET', 'POST'])
def novo_banco():
    if request.method == 'POST':
        nome = request.form.get('nome')
        num_conta = request.form.get('numero_conta')
        saldo_inicial = Decimal(request.form.get('saldo_inicial', '0.00'))
        conta_id = request.form.get('conta_contabil_id')
        
        try:
            if conta_id:
                # Caso o usuário tenha selecionado uma conta existente
                nova_conta = db.session.get(ContaContabil, int(conta_id))
            else:
                # Lógica atual de criação automática
                # 1. Encontrar conta pai (Bancos - 1.1)
                conta_pai = ContaContabil.query.filter_by(codigo='1.1').first()
                if not conta_pai:
                    conta_pai = ContaContabil.query.filter(ContaContabil.codigo.like('1.1%')).order_by(ContaContabil.codigo).first()
                
                if not conta_pai:
                    flash("Configuração Contábil Incompleta: Conta '1.1 - Bancos' não encontrada no Plano de Contas.", "error")
                    return redirect(url_for('financeiro.bancos'))

                # 2. Gerar próximo código
                prefixo = f"{conta_pai.codigo}."
                ultimas_contas = ContaContabil.query.filter(ContaContabil.codigo.like(f"{prefixo}%"))\
                    .order_by(ContaContabil.codigo.desc()).first()
                
                if ultimas_contas:
                    partes = ultimas_contas.codigo.split('.')
                    last_suffix = int(partes[-1])
                    new_suffix = str(last_suffix + 1).zfill(2)
                    novo_codigo = f"{conta_pai.codigo}.{new_suffix}"
                else:
                    novo_codigo = f"{conta_pai.codigo}.01"
                
                # 3. Criar Conta Contábil
                nova_conta = ContaContabil(
                    codigo=novo_codigo,
                    nome=nome,
                    tipo=TipoConta.ATIVO.value,
                    natureza='Devedora',
                    parent_id=conta_pai.id
                )
                db.session.add(nova_conta)
                db.session.flush()
            
            # 4. Criar Ativo
            novo_banco = Ativo(
                descricao=nome,
                tipo='Banco',
                numero_conta=num_conta,
                valor_atual=saldo_inicial,
                data_aquisicao=datetime.utcnow().date(),
                conta_contabil_id=nova_conta.id
            )
            db.session.add(novo_banco)
            
            # 5. Saldo Inicial
            if saldo_inicial > 0:
                conta_capital = ContaContabil.query.filter(ContaContabil.nome.like('%Capital%')).first()
                if not conta_capital:
                     conta_capital = ContaContabil.query.filter(ContaContabil.tipo == TipoConta.PATRIMONIO_LIQUIDO.value).first()
                
                if conta_capital:
                    FinancialService.realizar_transferencia_generica(
                        conta_debito_id=nova_conta.id,
                        conta_credito_id=conta_capital.id,
                        valor=saldo_inicial,
                        historico=f"Saldo Inicial - {nome}",
                        data=datetime.utcnow()
                    )
                else:
                    flash("Aviso: Banco criado, mas saldo inicial não foi lançado (Conta Capital não encontrada).", "info")
            
            db.session.commit()
            flash('Banco cadastrado com sucesso!', 'success')
            return redirect(url_for('financeiro.bancos'))
            
        except Exception as e:
            db.session.rollback()
            flash(f"Erro ao criar banco: {str(e)}", "error")
            return redirect(url_for('financeiro.bancos'))
            
    return render_template('financeiro/banco_form.html')

@financeiro_bp.route('/bancos/editar/<int:banco_id>', methods=['GET', 'POST'])
def editar_banco(banco_id):
    banco = db.session.get(Ativo, banco_id)
    if not banco:
        flash('Banco não encontrado.', 'error')
        return redirect(url_for('financeiro.bancos'))

    # Calcular saldo atual para exibir e comparar
    saldo_atual = 0
    if banco.conta_contabil_id:
        try:
            stmt = db.session.query(
                func.sum(PartidaDiario.valor).filter(PartidaDiario.tipo == 'D').label('debitos'),
                func.sum(PartidaDiario.valor).filter(PartidaDiario.tipo == 'C').label('creditos')
            ).filter(PartidaDiario.conta_id == banco.conta_contabil_id)
            res = stmt.first()
            if res:
                saldo_atual = (res.debitos or 0) - (res.creditos or 0)
        except: pass

    if request.method == 'POST':
        nome = request.form.get('nome')
        num_conta = request.form.get('numero_conta')
        novo_valor = Decimal(request.form.get('valor', '0.00'))
        conta_id = request.form.get('conta_contabil_id')

        try:
            # 1. Atualizar Campos Simples
            banco.descricao = nome
            banco.numero_conta = num_conta
            if conta_id:
                banco.conta_contabil_id = int(conta_id)
            
            if banco.conta_contabil:
                banco.conta_contabil.nome = nome
            
            # 2. Ajuste de Saldo (Contabilidade)
            if novo_valor != saldo_atual:
                diferenca = novo_valor - saldo_atual
                conta_ajustes = ContaContabil.query.filter(ContaContabil.nome.like('%Ajustes%')).first()
                if not conta_ajustes:
                    conta_ajustes = ContaContabil.query.filter(ContaContabil.tipo == TipoConta.PATRIMONIO_LIQUIDO.value).first()
                
                if diferenca > 0:
                    # Aumentar saldo: D: Banco / C: Ajustes
                    FinancialService.realizar_transferencia_generica(
                        conta_debito_id=banco.conta_contabil_id,
                        conta_credito_id=conta_ajustes.id,
                        valor=abs(diferenca),
                        historico=f"Ajuste de Saldo (Aumento) - {nome}",
                        data=datetime.utcnow()
                    )
                else:
                    # Diminuir saldo: D: Ajustes / C: Banco
                    FinancialService.realizar_transferencia_generica(
                        conta_debito_id=conta_ajustes.id,
                        conta_credito_id=banco.conta_contabil_id,
                        valor=abs(diferenca),
                        historico=f"Ajuste de Saldo (Redução) - {nome}",
                        data=datetime.utcnow()
                    )

            db.session.commit()
            flash('Banco atualizado com sucesso!', 'success')
            return redirect(url_for('financeiro.bancos'))
        except Exception as e:
            db.session.rollback()
            flash(f"Erro ao atualizar banco: {str(e)}", "error")
            return redirect(url_for('financeiro.bancos'))

    # Para edição, também carregar contas analíticas
    contas_banco = ContaContabil.query.filter(ContaContabil.tipo == TipoConta.ATIVO.value).all()
    contas_analiticas = [c for c in contas_banco if c.is_analitica]

    return render_template('financeiro/banco_form.html', 
                          banco=banco, 
                          saldo_atual=saldo_atual,
                          contas_contabeis=contas_analiticas)

@financeiro_bp.route('/bancos/extrato/<int:banco_id>')
def extrato_banco(banco_id):
    banco = db.session.get(Ativo, banco_id)
    if not banco or not banco.conta_contabil:
        flash('Banco não encontrado ou conta contábil não vinculada.', 'error')
        return redirect(url_for('financeiro.bancos'))

    page = request.args.get('page', 1, type=int)
    per_page = 50

    # Query base para as movimentações
    query = db.session.query(PartidaDiario, LivroDiario.data, LivroDiario.historico)\
        .join(LivroDiario, PartidaDiario.diario_id == LivroDiario.id)\
        .filter(PartidaDiario.conta_id == banco.conta_contabil_id)\
        .order_by(LivroDiario.data, LivroDiario.id)

    # Cálculo do saldo anterior (antes da página atual)
    offset = (page - 1) * per_page
    from sqlalchemy import case
    
    saldo_anterior = Decimal('0.00')
    if offset > 0:
        # Subquery para pegar apenas as IDs que viriam antes do offset
        subquery_prev = db.session.query(PartidaDiario.id)\
            .join(LivroDiario)\
            .filter(PartidaDiario.conta_id == banco.conta_contabil_id)\
            .order_by(LivroDiario.data, LivroDiario.id)\
            .limit(offset).subquery()
            
        saldo_anterior = db.session.query(
            func.sum(case((PartidaDiario.tipo == 'D', PartidaDiario.valor), else_=0)) -
            func.sum(case((PartidaDiario.tipo == 'C', PartidaDiario.valor), else_=0))
        ).select_from(PartidaDiario).filter(PartidaDiario.id.in_(subquery_prev)).scalar() or Decimal('0.00')

    # Paginação
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    partidas_page = pagination.items

    movimentacoes = []
    saldo_progressivo = saldo_anterior

    for p, data_lancamento, historico_lancamento in partidas_page:
        valor = p.valor
        tipo = p.tipo
        
        entrada = valor if tipo == 'D' else Decimal('0.00')
        saida = valor if tipo == 'C' else Decimal('0.00')
        
        saldo_progressivo += (entrada - saida)
        
        movimentacoes.append({
            'data': data_lancamento,
            'historico': historico_lancamento,
            'entrada': entrada,
            'saida': saida,
            'saldo': saldo_progressivo
        })

    # Saldo Final Real (Total geral da conta)
    saldo_final = db.session.query(
        func.sum(case((PartidaDiario.tipo == 'D', PartidaDiario.valor), else_=0)) -
        func.sum(case((PartidaDiario.tipo == 'C', PartidaDiario.valor), else_=0))
    ).filter(PartidaDiario.conta_id == banco.conta_contabil_id).scalar() or Decimal('0.00')

    return render_template('financeiro/extrato.html', 
                           banco=banco, 
                           movimentacoes=movimentacoes, 
                           pagination=pagination,
                           saldo_final=saldo_final)

@financeiro_bp.route('/venda', methods=['GET', 'POST'])
def nova_venda():
    next_url = request.args.get('next') or url_for('main.dashboard')
    
    if request.method == 'POST':
        try:
            entidade_id = int(request.form.get('entidade_id'))
            descricao = request.form.get('descricao')
            valor = Decimal(request.form.get('valor'))
            vencimento = datetime.strptime(request.form.get('data_vencimento'), '%Y-%m-%d')
            
            entidade = db.session.get(Entidade, entidade_id)
            FinancialService.criar_titulo_receber(entidade, descricao, valor, vencimento)
            
            db.session.commit()
            flash(f"Venda para '{entidade.nome}' registrada com sucesso!", "success")
            return redirect(next_url)
        except Exception as e:
            db.session.rollback()
            flash(f"Erro ao registrar venda: {str(e)}", "error")

    clientes = Entidade.query.filter_by(tipo=TipoEntidade.CLIENTE.value).all()
    if not clientes:
        flash("Nenhum Cliente cadastrado. Cadastre um cliente antes de realizar uma venda.", "info")
    
    hoje = datetime.utcnow().strftime('%Y-%m-%d')
    return render_template('financeiro/venda_form.html', clientes=clientes, hoje=hoje, next_url=next_url)

@financeiro_bp.route('/pagamento', methods=['GET', 'POST'])
def novo_pagamento():
    next_url = request.args.get('next') or url_for('main.dashboard')

    if request.method == 'POST':
        try:
            entidade_id = int(request.form.get('entidade_id'))
            descricao = request.form.get('descricao')
            valor = Decimal(request.form.get('valor'))
            vencimento = datetime.strptime(request.form.get('data_vencimento'), '%Y-%m-%d')
            
            entidade = db.session.get(Entidade, entidade_id)
            FinancialService.criar_titulo_pagar(entidade, descricao, valor, vencimento)
            
            db.session.commit()
            flash(f"Conta a pagar para '{entidade.nome}' registrada com sucesso!", "success")
            return redirect(next_url)
        except Exception as e:
            db.session.rollback()
            flash(f"Erro ao registrar pagamento: {str(e)}", "error")

    fornecedores = Entidade.query.filter_by(tipo=TipoEntidade.FORNECEDOR.value).all()
    
    if not fornecedores:
        flash("Nenhum Fornecedor cadastrado.", "info")
    
    hoje = datetime.utcnow().strftime('%Y-%m-%d')
    return render_template('financeiro/pagamento_form.html', fornecedores=fornecedores, hoje=hoje, next_url=next_url)

@financeiro_bp.route('/movimentacao-outros', methods=['GET', 'POST'])
def movimentacao_outros():
    next_url = request.args.get('next') or url_for('main.dashboard')

    if request.method == 'POST':
        try:
            entidade_id_raw = request.form.get('entidade_id')
            entidade_id = int(entidade_id_raw) if entidade_id_raw else None
            
            descricao = request.form.get('descricao')
            valor = Decimal(request.form.get('valor'))
            data_contabil = datetime.strptime(request.form.get('data_contabil'), '%Y-%m-%d')
            data_vencimento = datetime.strptime(request.form.get('data_vencimento'), '%Y-%m-%d')
            tipo_mov = request.form.get('tipo_movimentacao') # 'Receber' (Vem $ p/ Banco) ou 'Pagar' (Sai $ do Banco)
            banco_id = int(request.form.get('banco_id'))
            num_parcelas = int(request.form.get('num_parcelas', 1))
            
            categoria_contrapartida = request.form.get('categoria_contrapartida', 'PASSIVO')
            conta_pl_id = request.form.get('conta_pl_id')
            
            entidade = db.session.get(Entidade, entidade_id) if entidade_id else None
            
            FinancialService.registrar_movimentacao_outros(
                entidade=entidade,
                descricao=descricao,
                valor=valor,
                banco_id=banco_id,
                data_contabil=data_contabil,
                data_vencimento_base=data_vencimento,
                tipo_mov=tipo_mov,
                num_parcelas=num_parcelas,
                categoria_contrapartida=categoria_contrapartida,
                conta_pl_id=conta_pl_id
            )
            
            db.session.commit()
            flash(f"Movimentação '{descricao}' registrada com sucesso!", "success")
            return redirect(next_url)
        except Exception as e:
            db.session.rollback()
            flash(f"Erro ao registrar movimentação: {str(e)}", "error")

    entidades = Entidade.query.all()
    bancos = Ativo.query.filter_by(tipo=TipoAtivo.BANCO.value).all()
    contas_pl = ContaContabil.query.filter(ContaContabil.tipo == 'Patrimônio Líquido').all()
    
    hoje = datetime.utcnow().strftime('%Y-%m-%d')
    return render_template('financeiro/movimentacao_outros_form.html', 
                           entidades=entidades, 
                           bancos=bancos, 
                           contas_pl=contas_pl,
                           hoje=hoje, 
                           next_url=next_url)

@financeiro_bp.route('/estornar/<int:titulo_id>')
def estornar_titulo_route(titulo_id):
    # ... (manter original para compatibilidade com a lista de títulos)
    try:
        titulo = db.session.get(Titulo, titulo_id)
        if not titulo:
            flash("Título não encontrado.", "error")
            return redirect(url_for('financeiro.titulos'))

        hoje = datetime.utcnow().date()
        data_limite = hoje - timedelta(days=60)
        
        if titulo.data_emissao < data_limite:
            flash("Segurança: Não é permitido estornar títulos com mais de 2 meses.", "warning")
            return redirect(url_for('financeiro.titulos'))

        FinancialService.estornar_titulo(titulo)
        db.session.commit()
        flash(f"Título '{titulo.descricao}' estornado com sucesso!", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Erro ao estornar título: {str(e)}", "error")
        
    return redirect(url_for('financeiro.titulos'))

# --- API ROUTES PARA AJAX ---

@financeiro_bp.route('/api/titulo/<int:titulo_id>')
def get_titulo_api(titulo_id):
    titulo = db.session.get(Titulo, titulo_id)
    if not titulo:
        return {"error": "Título não encontrado"}, 404
        
    bancos = Ativo.query.filter_by(tipo='Banco').all()
    
    return {
        "id": titulo.id,
        "descricao": titulo.descricao,
        "valor": float(titulo.valor),
        "data_vencimento": titulo.data_vencimento.strftime('%d/%m/%Y'),
        "data_vencimento_iso": titulo.data_vencimento.strftime('%Y-%m-%d'),
        "status": titulo.status,
        "tipo": titulo.tipo,
        "entidade": titulo.entidade.nome if titulo.entidade else "N/A",
        "bancos": [{"id": b.id, "nome": b.descricao} for b in bancos]
    }

@financeiro_bp.route('/api/liquidar/<int:titulo_id>', methods=['POST'])
def liquidar_titulo_api(titulo_id):
    titulo = db.session.get(Titulo, titulo_id)
    if not titulo:
        return {"success": False, "message": "Título não encontrado"}, 404
        
    try:
        data = request.get_json()
        banco_id = int(data.get('banco_id'))
        data_pagamento = datetime.strptime(data.get('data_pagamento'), '%Y-%m-%d')
        
        FinancialService.liquidar_titulo(titulo, banco_id, data_pagamento)
        db.session.commit()
        return {"success": True, "message": f"Título '{titulo.descricao}' liquidado com sucesso!"}
    except Exception as e:
        db.session.rollback()
        return {"success": False, "message": str(e)}, 400

@financeiro_bp.route('/api/estornar/<int:titulo_id>', methods=['POST'])
def estornar_titulo_api(titulo_id):
    titulo = db.session.get(Titulo, titulo_id)
    if not titulo:
        return {"success": False, "message": "Título não encontrado"}, 404
        
    try:
        FinancialService.estornar_titulo(titulo)
        db.session.commit()
        return {"success": True, "message": f"Título '{titulo.descricao}' estornado com sucesso!"}
    except Exception as e:
        db.session.rollback()
        return {"success": False, "message": str(e)}, 400
