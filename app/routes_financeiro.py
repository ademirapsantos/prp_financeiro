from flask import Blueprint, render_template, request, redirect, url_for, flash
from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy import func
from .models import Titulo, Ativo, ContaContabil, TipoConta, TipoTitulo, StatusTitulo, PartidaDiario, LivroDiario, Entidade, TipoEntidade, TipoAtivo, Configuracao, db, CartaoCredito, TransacaoCartao, FaturaCartao
from .services import FinancialService
from flask_login import current_user, login_required

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

    # Definir status com base na aba
    status_alvo = StatusTitulo.PAGO.value if active_tab == 'pagas' else StatusTitulo.ABERTO.value
    if status_filtro:
        status_alvo = status_filtro

    # Query base para os totais (sem paginação, mas com filtros)
    total_query = db.session.query(
        func.sum(Titulo.valor).filter(Titulo.tipo == TipoTitulo.RECEBER.value, Titulo.status == status_alvo).label('receber'),
        func.sum(Titulo.valor).filter(Titulo.tipo == TipoTitulo.PAGAR.value, Titulo.status == status_alvo).label('pagar')
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
        query = query.filter(Titulo.status == status_alvo)
        total_query = total_query.filter(Titulo.status == status_alvo)

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
    data_limite_estorno_20 = hoje - timedelta(days=20)
    
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
                         data_limite_estorno_20=data_limite_estorno_20,
                         active_tab=active_tab)

@financeiro_bp.route('/bancos/<int:banco_id>')
@login_required
def detalhes_banco(banco_id):
    banco = Ativo.query.get_or_404(banco_id)
    cartoes = CartaoCredito.query.filter_by(banco_id=banco.id).all()
    
    # Buscar todas as faturas dos cartões deste banco para o filtro
    card_ids = [c.id for c in cartoes]
    faturas = FaturaCartao.query.filter(FaturaCartao.card_id.in_(card_ids)).order_by(FaturaCartao.competencia.desc()).all()
    
    fatura_id = request.args.get('fatura_id', type=int)
    fatura_selecionada = None
    
    if fatura_id:
        fatura_selecionada = FaturaCartao.query.get(fatura_id)
    
    # Se não houver fatura selecionada, busca a primeira 'aberta' ou 'fechada' (não paga)
    if not fatura_selecionada and faturas:
        fatura_selecionada = next((f for f in faturas if f.situacao_pagamento != 'paga'), faturas[0])
    
    # Filtrar transações por fatura
    query = TransacaoCartao.query.join(CartaoCredito).filter(CartaoCredito.banco_id == banco_id)
    
    if fatura_selecionada:
        query = query.filter(TransacaoCartao.fatura_id == fatura_selecionada.id)
    
    transacoes = query.order_by(TransacaoCartao.data.desc()).all()
    
    # Categorias de despesa para o modal de compra (Apenas analíticas)
    categorias = [c for c in ContaContabil.query.filter_by(tipo=TipoConta.DESPESA.value).order_by(ContaContabil.codigo).all() if c.is_analitica]
    
    # Contas de passivo para o modal de novo cartão (Apenas analíticas)
    contas_passivo = [c for c in ContaContabil.query.filter_by(tipo=TipoConta.PASSIVO.value).order_by(ContaContabil.codigo).all() if c.is_analitica]
    
    hoje_str = datetime.utcnow().strftime('%Y-%m-%d')
    bancos_pagamento = Ativo.query.filter_by(tipo=TipoAtivo.BANCO.value).all()
    
    # Faturas elegíveis para pagamento (Lookup)
    faturas_pagamento = FaturaCartao.query.filter(
        FaturaCartao.card_id.in_(card_ids),
        FaturaCartao.situacao_pagamento != 'paga'
    ).order_by(FaturaCartao.data_vencimento.asc()).all()
    # Filtrar faturas_pagamento para garantir que total_pago < total (considerando Decimal)
    faturas_pagamento = [f for f in faturas_pagamento if (f.total_pago or 0) < f.total]
    
    return render_template('financeiro/detalhes_banco.html', 
                         banco=banco, 
                         cartoes=cartoes,
                         faturas=faturas,
                         faturas_pagamento=faturas_pagamento,
                         fatura_selecionada=fatura_selecionada,
                         categorias=categorias,
                         contas_passivo=contas_passivo,
                         transacoes=transacoes,
                         hoje_str=hoje_str,
                         bancos=bancos_pagamento)

@financeiro_bp.route('/cadastrar_cartao', methods=['POST'])
@login_required
def cadastrar_cartao():
    banco_id = request.form.get('banco_id')
    nome = request.form.get('nome')
    bandeira = request.form.get('bandeira')
    limite = request.form.get('limite')
    fechamento = request.form.get('fechamento')
    vencimento = request.form.get('vencimento')
    conta_contabil_id = request.form.get('conta_contabil_id')
    
    try:
        novo_cartao = CartaoCredito(
            user_id=current_user.id,
            banco_id=banco_id,
            nome=nome,
            bandeira=bandeira,
            limite_total=Decimal(limite.replace('.', '').replace(',', '.')),
            limite_disponivel=Decimal(limite.replace('.', '').replace(',', '.')), # Inicializa limite disponível
            perc_limite_emergencial=Decimal(request.form.get('perc_emergencial', '0').replace('.', '').replace(',', '.')),
            limite_emergencial_ativo=bool(request.form.get('emergencial_ativo')),
            dia_fechamento=int(fechamento),
            dia_vencimento=int(vencimento),
            conta_contabil_id=conta_contabil_id
        )
        
        db.session.add(novo_cartao)
        db.session.commit()

        # Garantir criação da fatura inicial para o novo cartão
        from .services import CreditCardService
        CreditCardService.obter_fatura_para_data(novo_cartao, datetime.utcnow())
        db.session.commit()
        flash('Cartão cadastrado com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao cadastrar cartão: {str(e)}', 'error')
        
@financeiro_bp.route('/editar_cartao/<int:cartao_id>', methods=['POST'])
@login_required
def editar_cartao(cartao_id):
    cartao = CartaoCredito.query.get_or_404(cartao_id)
    limite = request.form.get('limite')
    fechamento = request.form.get('fechamento')
    vencimento = request.form.get('vencimento')
    conta_contabil_id = request.form.get('conta_contabil_id')
    
    try:
        # Remove pontos de milhar e substitui vírgula decimal por ponto para conversão Decimal
        limite_processado = limite.replace('.', '').replace(',', '.')
        cartao.limite_total = Decimal(limite_processado)
        cartao.dia_fechamento = int(fechamento)
        cartao.dia_vencimento = int(vencimento)
        cartao.conta_contabil_id = int(conta_contabil_id)
        cartao.perc_limite_emergencial = Decimal(request.form.get('perc_emergencial', '0').replace(',', '.'))
        cartao.limite_emergencial_ativo = bool(request.form.get('emergencial_ativo'))
        
        # Ajustar limite disponível se necessário
        if cartao.limite_disponivel > cartao.limite_maximo_total:
            cartao.limite_disponivel = cartao.limite_maximo_total
        
        db.session.commit()
        flash('Configurações do cartão atualizadas com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao atualizar cartão: {str(e)}', 'error')
        
    return redirect(url_for('financeiro.detalhes_banco', banco_id=cartao.banco_id))

@financeiro_bp.route('/lancar_compra_cartao', methods=['POST'])
@login_required
def lancar_compra_cartao():
    cartao_id = request.form.get('cartao_id')
    descricao = request.form.get('descricao')
    valor = request.form.get('valor')
    categoria_id = request.form.get('categoria_id')
    data_compra_str = request.form.get('data_compra')
    num_parcelas = request.form.get('num_parcelas', '1')
    
    cartao = CartaoCredito.query.get_or_404(cartao_id)
    data_compra = datetime.strptime(data_compra_str, '%Y-%m-%d')
    valor_decimal = Decimal(valor.replace('.', '').replace(',', '.'))
    
    try:
        from .services import CreditCardService
        CreditCardService.registrar_compra(
            cartao=cartao,
            descricao=descricao,
            valor=valor_decimal,
            categoria_id=int(categoria_id),
            data_compra=data_compra,
            num_parcelas=int(num_parcelas)
        )
        db.session.commit()
        flash('Compra registrada com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao registrar compra: {str(e)}', 'error')
        
    return redirect(url_for('financeiro.detalhes_banco', banco_id=cartao.banco_id))

@financeiro_bp.route('/estornar_cartao/<int:transacao_id>', methods=['POST'])
@login_required
def estornar_transacao_cartao(transacao_id):
    from .services import CreditCardService
    try:
        sucesso, mensagem = CreditCardService.estornar_compra(transacao_id)
        if sucesso:
            db.session.commit()
            flash(mensagem, 'success')
        else:
            flash(mensagem, 'error')
    except Exception as e:
        db.session.rollback()
        flash(f"Erro ao estornar compra: {str(e)}", 'error')
    
    from .models import TransacaoCartao
    trans = db.session.get(TransacaoCartao, transacao_id)
    if trans:
        return redirect(url_for('financeiro.detalhes_banco', banco_id=trans.cartao.banco_id))
    return redirect(url_for('financeiro.bancos'))


@financeiro_bp.route('/pagar_fatura_cartao', methods=['POST'])
@login_required
def pagar_fatura_cartao():
    fatura_id = request.form.get('fatura_id')
    banco_ativo_id = request.form.get('banco_ativo_id')
    valor_fatura = request.form.get('valor_fatura')
    valor_encargos = request.form.get('valor_encargos', '0')
    conta_encargos_id = request.form.get('conta_encargos_id')
    data_pagamento_str = request.form.get('data_pagamento')
    
    banco = Ativo.query.get_or_404(banco_ativo_id)
    data_pagamento = datetime.strptime(data_pagamento_str, '%Y-%m-%d')
    valor_fatura_dec = Decimal(valor_fatura.replace('.', '').replace(',', '.'))
    valor_encargos_dec = Decimal(valor_encargos.replace('.', '').replace(',', '.'))
    
    fatura = FaturaCartao.query.get_or_404(fatura_id)
    cartao = fatura.cartao

    try:
        from .services import CreditCardService
        CreditCardService.realizar_pagamento_fatura(
            fatura_id=fatura.id,
            banco=banco,
            valor_fatura=valor_fatura_dec,
            valor_encargos=valor_encargos_dec,
            conta_encargos_id=conta_encargos_id,
            data_pagamento=data_pagamento
        )
        db.session.commit()
        flash(f'Pagamento da fatura {fatura.competencia} realizado com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao realizar pagamento: {str(e)}', 'error')
        
    return redirect(url_for('financeiro.detalhes_banco', banco_id=cartao.banco_id))

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
            valor_desconto = request.form.get('valor_desconto', '0')
            valor_desconto_dec = Decimal(valor_desconto.replace('.', '').replace(',', '.'))
            
            FinancialService.liquidar_titulo(titulo, banco_id, data_pagamento, valor_desconto=valor_desconto_dec)
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
            
            redirect_to = request.form.get('redirect_to', 'main.dashboard')
            flash('Transferência realizada com sucesso!', 'success')
            
            if redirect_to == 'bancos':
                return redirect(url_for('financeiro.bancos'))
            return redirect(url_for('main.dashboard'))
            
        except Exception as e:
            db.session.rollback()
            flash(f"Erro na transferência: {str(e)}", "error")
            return redirect(url_for('financeiro.transferencia'))

    # Carregar contas do Ativo (Bancos/Caixa)
    contas = ContaContabil.query.filter(ContaContabil.tipo == TipoConta.ATIVO.value).all()
    contas_selecionaveis = [c for c in contas if c.is_analitica]
    
    origem_id = request.args.get('origem_id')
    redirect_to = request.args.get('redirect', 'dashboard')
    hoje_str = datetime.utcnow().strftime('%Y-%m-%d')
    
    return render_template('financeiro/transferencia.html', 
                         contas=contas_selecionaveis, 
                         hoje_str=hoje_str,
                         origem_pre_selecionada=origem_id,
                         redirect_to=redirect_to)

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
                # Buscar conta de contrapartida via Parâmetros (Configuracao)
                conta_pl_id = Configuracao.get_valor('conta_ativo_banco')
                conta_capital = None
                
                if conta_pl_id:
                    conta_capital = db.session.get(ContaContabil, int(conta_pl_id))
                
                # Fallback se não estiver configurado (manter busca por texto mas validar analítica)
                if not conta_capital:
                    conta_capital = ContaContabil.query.filter(
                        ContaContabil.nome.like('%Capital%'),
                        ContaContabil.is_analitica == True
                    ).first()
                
                if not conta_capital:
                     conta_capital = ContaContabil.query.filter(
                         ContaContabil.tipo == TipoConta.PATRIMONIO_LIQUIDO.value,
                         ContaContabil.is_analitica == True
                     ).first()
                
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
                
                # Buscar conta de contrapartida via Parâmetros (Configuracao)
                conta_pl_id = Configuracao.get_valor('conta_ativo_banco')
                conta_ajustes = None
                
                if conta_pl_id:
                    conta_ajustes = db.session.get(ContaContabil, int(conta_pl_id))

                if not conta_ajustes:
                    conta_ajustes = ContaContabil.query.filter(
                        ContaContabil.nome.like('%Ajustes%'),
                        ContaContabil.is_analitica == True
                    ).first()
                
                if not conta_ajustes:
                    conta_ajustes = ContaContabil.query.filter(
                        ContaContabil.tipo == TipoConta.PATRIMONIO_LIQUIDO.value,
                        ContaContabil.is_analitica == True
                    ).first()
                
                if not conta_ajustes:
                    raise ValueError("Nenhuma conta de contrapartida (PL) encontrada para o ajuste. Verifique os Parâmetros Contábeis.")
                
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
        if titulo.status in ['Pago', 'PAGO']:
            data_liq = titulo.data_liquidacao
            if data_liq:
                data_limite_20 = hoje - timedelta(days=20)
                if data_liq < data_limite_20:
                    flash(f"Segurança: Títulos liquidados há mais de 20 dias ({data_liq.strftime('%d/%m/%Y')}) não podem ser estornados.", "warning")
                    return redirect(url_for('financeiro.titulos'))

        data_limite_60 = hoje - timedelta(days=60)
        if titulo.data_emissao < data_limite_60:
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
        hoje = datetime.utcnow().date()
        
        # Validar trava de 20 dias para títulos pagos
        if titulo.status in ['Pago', 'PAGO']:
            data_liq = titulo.data_liquidacao
            if data_liq:
                data_limite_20 = hoje - timedelta(days=20)
                if data_liq < data_limite_20:
                    return {"success": False, "message": f"Segurança: Estorno bloqueado. Título liquidado há mais de 20 dias ({data_liq.strftime('%d/%m/%Y')})."}, 400

        # Validar trava geral de 60 dias
        data_limite_60 = hoje - timedelta(days=60)
        if titulo.data_emissao < data_limite_60:
             return {"success": False, "message": "Segurança: Não é permitido estornar títulos com mais de 2 meses."}, 400

        FinancialService.estornar_titulo(titulo)
        db.session.commit()
        return {"success": True, "message": f"Título '{titulo.descricao}' estornado com sucesso!"}
    except Exception as e:
        db.session.rollback()
        return {"success": False, "message": str(e)}, 400
