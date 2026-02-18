from flask import Blueprint, render_template, request, redirect, url_for, flash
from datetime import datetime
from decimal import Decimal
from .models import Ativo, TipoAtivo, Entidade, ContaContabil, TipoEntidade, TipoConta, PartidaDiario, db
from sqlalchemy import func
from .services import AssetService

ativos_bp = Blueprint('ativos', __name__, url_prefix='/ativos')

@ativos_bp.route('/')
def lista():
    page = request.args.get('page', 1, type=int)
    per_page = 50
    descricao = request.args.get('descricao', '')
    conta_contabil_id = request.args.get('conta_contabil_id', '')

    query = Ativo.query

    if descricao:
        query = query.filter(Ativo.descricao.ilike(f"%{descricao}%"))
    
    if conta_contabil_id:
        query = query.filter(Ativo.conta_contabil_id == int(conta_contabil_id))
    
    pagination = query.order_by(Ativo.data_aquisicao.desc(), Ativo.id.desc()).paginate(page=page, per_page=per_page, error_out=False)
    ativos_raw = pagination.items
    
    # Calcular saldo real para cada ativo da página e sincronizar valor_atual
    ativos = []
    for a in ativos_raw:
        saldo = float(a.valor_atual)
        if a.conta_contabil_id:
            res = db.session.query(
                func.sum(PartidaDiario.valor).filter(PartidaDiario.tipo == 'D').label('debitos'),
                func.sum(PartidaDiario.valor).filter(PartidaDiario.tipo == 'C').label('creditos')
            ).filter(PartidaDiario.conta_id == a.conta_contabil_id).first()
            
            saldo = float((res.debitos or 0) - (res.creditos or 0))
            
            # Sincronizar campo no DB se houver divergência
            if float(a.valor_atual) != saldo:
                a.valor_atual = saldo
                db.session.add(a)

        ativos.append(a)
    
    if db.session.dirty:
        db.session.commit()
    
    # Precisamos das contas de ativo para o filtro
    contas_ativo = ContaContabil.query.filter(ContaContabil.tipo == TipoConta.ATIVO.value).all()
    
    # Dados para o Modal de Venda
    compradores = Entidade.query.filter(
        (Entidade.tipo == TipoEntidade.CLIENTE.value) |
        ((Entidade.tipo == TipoEntidade.OUTROS.value) & 
         (Entidade.conta_venda_id.isnot(None)) & 
         (Entidade.conta_compra_id.isnot(None)))
    ).all()
    from datetime import date
    today = date.today().strftime('%Y-%m-%d')
    
    filtros = {
        'descricao': descricao,
        'conta_contabil_id': conta_contabil_id
    }
    
    return render_template('ativos/lista.html', 
                         ativos=ativos, 
                         pagination=pagination,
                         contas_ativo=contas_ativo,
                         compradores=compradores,
                         today=today,
                         filtros=filtros)

@ativos_bp.route('/novo', methods=['GET', 'POST'])
def novo():
    if request.method == 'POST':
        try:
            descricao = request.form.get('descricao')
            tipo = request.form.get('tipo')
            dt_aquisicao_str = request.form.get('data_aquisicao')
            dt_aquisicao = datetime.strptime(dt_aquisicao_str, '%Y-%m-%d').date() if dt_aquisicao_str else datetime.utcnow().date()
            
            fornecedor_id = request.form.get('fornecedor_id')
            conta_ativo_id = request.form.get('conta_ativo_id')
            fornecedor = db.session.get(Entidade, fornecedor_id)

            if tipo == TipoAtivo.INVESTIMENTO.value:
                valor_unitario = Decimal(request.form.get('valor_unitario', '0.00'))
                quantidade = float(request.form.get('quantidade', '0'))
                banco_ativo_id = request.form.get('banco_ativo_id')
                
                AssetService.comprar_investimento(
                    descricao=descricao,
                    valor_unitario=valor_unitario,
                    quantidade=quantidade,
                    entidade_vendedor=fornecedor,
                    data_aquisicao=dt_aquisicao,
                    conta_ativo_id=int(conta_ativo_id),
                    banco_ativo_id=int(banco_ativo_id)
                )
            else:
                valor = Decimal(request.form.get('valor', '0.00'))
                num_parcelas = int(request.form.get('num_parcelas', 1))
                valor_juros = Decimal(request.form.get('valor_juros', '0.00'))
                dt_primeira_parcela_str = request.form.get('data_primeiro_vencimento')
                dt_primeira_parcela = datetime.strptime(dt_primeira_parcela_str, '%Y-%m-%d').date() if dt_primeira_parcela_str else dt_aquisicao
                
                AssetService.comprar_ativo_imobilizado(
                    descricao=descricao,
                    valor=valor,
                    entidade_fornecedor=fornecedor,
                    data_aquisicao=dt_aquisicao,
                    conta_ativo_id=int(conta_ativo_id),
                    tipo_ativo=tipo,
                    num_parcelas=num_parcelas,
                    data_primeiro_vencimento=dt_primeira_parcela,
                    valor_juros=valor_juros
                )
            
            db.session.commit()
            flash('Ativo cadastrado com sucesso!', 'success')
            return redirect(url_for('ativos.lista'))
            
        except Exception as e:
            db.session.rollback()
            flash(f"Erro ao cadastrar ativo: {str(e)}", "error")
            return redirect(url_for('ativos.novo'))

    # Carregar dados para o form
    fornecedores = Entidade.query.filter(Entidade.tipo == TipoEntidade.FORNECEDOR.value).all()
    contas_ativo = ContaContabil.query.filter(ContaContabil.tipo == TipoConta.ATIVO.value).all()
    bancos = Ativo.query.filter(Ativo.tipo == TipoAtivo.BANCO.value).all()
    
    return render_template('ativos/form.html', 
                         fornecedores=fornecedores, 
                         contas_ativo=contas_ativo,
                         tipos_ativo=TipoAtivo,
                         bancos=bancos)

@ativos_bp.route('/venda/<int:ativo_id>', methods=['GET', 'POST'])
def venda(ativo_id):
    ativo = db.session.get(Ativo, ativo_id)
    if request.method == 'POST':
        try:
            comprador_id = request.form.get('comprador_id')
            comprador = db.session.get(Entidade, comprador_id)
            data_venda = datetime.strptime(request.form.get('data_venda'), '%Y-%m-%d').date()
            
            if ativo.tipo == TipoAtivo.INVESTIMENTO.value:
                quantidade = float(request.form.get('quantidade'))
                valor_unitario = Decimal(request.form.get('valor_unitario'))
                AssetService.vender_investimento(ativo.id, comprador, quantidade, valor_unitario, data_venda)
            else:
                valor_venda = Decimal(request.form.get('valor_venda'))
                num_parcelas = int(request.form.get('num_parcelas', 1))
                primeiro_venc = request.form.get('data_primeiro_vencimento')
                dt_primeiro = datetime.strptime(primeiro_venc, '%Y-%m-%d').date() if primeiro_venc else data_venda
                AssetService.vender_ativo(ativo.id, comprador, valor_venda, data_venda, num_parcelas, dt_primeiro)
            
            db.session.commit()
            flash('Venda registrada com sucesso! Títulos a receber gerados.', 'success')
            return redirect(url_for('ativos.lista'))
        except Exception as e:
            db.session.rollback()
            flash(f"Erro ao registrar venda: {str(e)}", "error")
            
    compradores = Entidade.query.filter(Entidade.tipo == TipoEntidade.CLIENTE.value).all()
    from datetime import date
    return render_template('ativos/venda_form.html', ativo=ativo, compradores=compradores, today=date.today())

@ativos_bp.route('/recompra/<int:ativo_id>', methods=['GET', 'POST'])
def recompra(ativo_id):
    ativo = db.session.get(Ativo, ativo_id)
    if request.method == 'POST':
        try:
            quantidade = float(request.form.get('quantidade'))
            valor_unitario = Decimal(request.form.get('valor_unitario'))
            banco_id = request.form.get('banco_ativo_id')
            data_acq = datetime.strptime(request.form.get('data_aquisicao'), '%Y-%m-%d').date()
            
            AssetService.recomprar_investimento(ativo.id, valor_unitario, quantidade, data_acq, int(banco_id))
            db.session.commit()
            flash('Aporte/Recompra realizado com sucesso!', 'success')
            return redirect(url_for('ativos.lista'))
        except Exception as e:
            db.session.rollback()
            flash(f"Erro ao registrar recompra: {str(e)}", "error")
            
    bancos = Ativo.query.filter(Ativo.tipo == TipoAtivo.BANCO.value).all()
    from datetime import date
    return render_template('ativos/recompra_form.html', ativo=ativo, bancos=bancos, today=date.today())

@ativos_bp.route('/estornar/<int:ativo_id>')
def estornar(ativo_id):
    success, message = AssetService.estornar_compra_ativo(ativo_id)
    if success:
        flash(message, 'success')
        db.session.commit()
    else:
        flash(message, 'danger')
        db.session.rollback()
    
    return redirect(url_for('ativos.lista'))
