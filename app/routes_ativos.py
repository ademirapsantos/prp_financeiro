from flask import Blueprint, render_template, request, redirect, url_for, flash
from datetime import datetime
from decimal import Decimal
from sqlalchemy import func

from .models import (
    Ativo,
    TipoAtivo,
    Entidade,
    ContaContabil,
    TipoEntidade,
    TipoConta,
    PartidaDiario,
    db,
)
from .services import AssetService

ativos_bp = Blueprint('ativos', __name__, url_prefix='/ativos')


def _sincronizar_saldo_banco(ativo):
    if ativo.tipo != TipoAtivo.BANCO.value or not ativo.conta_contabil_id:
        return ativo

    res = db.session.query(
        func.sum(PartidaDiario.valor).filter(PartidaDiario.tipo == 'D').label('debitos'),
        func.sum(PartidaDiario.valor).filter(PartidaDiario.tipo == 'C').label('creditos'),
    ).filter(PartidaDiario.conta_id == ativo.conta_contabil_id).first()

    saldo = float((res.debitos or 0) - (res.creditos or 0))
    if float(ativo.valor_atual) != saldo:
        ativo.valor_atual = saldo
        db.session.add(ativo)

    return ativo


def _get_redirect_destino(default_endpoint, **default_values):
    next_url = request.values.get('next_url')
    if next_url:
        return next_url
    return url_for(default_endpoint, **default_values)


def _listar_compradores_ativos():
    return Entidade.query.filter(
        (Entidade.tipo == TipoEntidade.CLIENTE.value)
        | (
            (Entidade.tipo == TipoEntidade.OUTROS.value)
            & (Entidade.conta_venda_id.isnot(None))
            & (Entidade.conta_compra_id.isnot(None))
        )
    ).all()


@ativos_bp.route('/')
def lista():
    page = request.args.get('page', 1, type=int)
    per_page = 50
    descricao = request.args.get('descricao', '')
    conta_contabil_id = request.args.get('conta_contabil_id', '')
    tipo = request.args.get('tipo', '')
    tipos_com_totalizador = {
        TipoAtivo.INVESTIMENTO.value,
        TipoAtivo.IMOVEL.value,
        TipoAtivo.VEICULO.value,
        TipoAtivo.OUTROS.value,
    }

    query = Ativo.query

    if descricao:
        query = query.filter(Ativo.descricao.ilike(f"%{descricao}%"))

    if conta_contabil_id:
        query = query.filter(Ativo.conta_contabil_id == conta_contabil_id)

    if tipo:
        query = query.filter(Ativo.tipo == tipo)

    totalizador_valor = None
    if tipo in tipos_com_totalizador:
        totalizador_valor = (
            query.with_entities(func.coalesce(func.sum(Ativo.valor_atual), 0)).scalar()
        )

    pagination = query.order_by(Ativo.data_aquisicao.desc(), Ativo.id.desc()).paginate(
        page=page,
        per_page=per_page,
        error_out=False,
    )
    ativos_raw = pagination.items

    ativos = []
    for ativo in ativos_raw:
        ativos.append(_sincronizar_saldo_banco(ativo))

    if db.session.dirty:
        db.session.commit()

    contas_ativo = ContaContabil.query.filter(
        ContaContabil.tipo == TipoConta.ATIVO.value
    ).all()

    from datetime import date

    filtros = {
        'descricao': descricao,
        'conta_contabil_id': conta_contabil_id,
        'tipo': tipo,
    }

    return render_template(
        'ativos/lista.html',
        ativos=ativos,
        pagination=pagination,
        contas_ativo=contas_ativo,
        tipos_ativo=TipoAtivo,
        compradores=_listar_compradores_ativos(),
        today=date.today().strftime('%Y-%m-%d'),
        filtros=filtros,
        mostrar_totalizador=tipo in tipos_com_totalizador,
        totalizador_valor=totalizador_valor,
    )


@ativos_bp.route('/detalhe/<ativo_id>')
def detalhe(ativo_id):
    ativo = db.session.get(Ativo, ativo_id)
    if not ativo:
        flash('Ativo nao encontrado.', 'error')
        return redirect(url_for('ativos.lista'))

    ativo = _sincronizar_saldo_banco(ativo)
    if db.session.dirty:
        db.session.commit()

    from datetime import date

    bancos = Ativo.query.filter(Ativo.tipo == TipoAtivo.BANCO.value).order_by(Ativo.descricao.asc()).all()

    return render_template(
        'ativos/detalhe.html',
        ativo=ativo,
        compradores=_listar_compradores_ativos(),
        bancos=bancos,
        today=date.today().strftime('%Y-%m-%d'),
    )


@ativos_bp.route('/novo', methods=['GET', 'POST'])
def novo():
    if request.method == 'POST':
        try:
            descricao = request.form.get('descricao')
            tipo = request.form.get('tipo')
            dt_aquisicao_str = request.form.get('data_aquisicao')
            dt_aquisicao = (
                datetime.strptime(dt_aquisicao_str, '%Y-%m-%d').date()
                if dt_aquisicao_str
                else datetime.utcnow().date()
            )

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
                    conta_ativo_id=conta_ativo_id,
                    banco_ativo_id=banco_ativo_id,
                )
            else:
                valor = Decimal(request.form.get('valor', '0.00'))
                num_parcelas = int(request.form.get('num_parcelas', 1))
                valor_juros = Decimal(request.form.get('valor_juros', '0.00'))
                dt_primeira_parcela_str = request.form.get('data_primeiro_vencimento')
                dt_primeira_parcela = (
                    datetime.strptime(dt_primeira_parcela_str, '%Y-%m-%d').date()
                    if dt_primeira_parcela_str
                    else dt_aquisicao
                )

                AssetService.comprar_ativo_imobilizado(
                    descricao=descricao,
                    valor=valor,
                    entidade_fornecedor=fornecedor,
                    data_aquisicao=dt_aquisicao,
                    conta_ativo_id=conta_ativo_id,
                    tipo_ativo=tipo,
                    num_parcelas=num_parcelas,
                    data_primeiro_vencimento=dt_primeira_parcela,
                    valor_juros=valor_juros,
                )

            db.session.commit()
            flash('Ativo cadastrado com sucesso!', 'success')
            return redirect(url_for('ativos.lista'))

        except Exception as e:
            db.session.rollback()
            flash(f"Erro ao cadastrar ativo: {str(e)}", "error")
            return redirect(url_for('ativos.novo'))

    fornecedores = Entidade.query.filter(Entidade.tipo == TipoEntidade.FORNECEDOR.value).all()
    contas_ativo = ContaContabil.query.filter(ContaContabil.tipo == TipoConta.ATIVO.value).all()
    bancos = Ativo.query.filter(Ativo.tipo == TipoAtivo.BANCO.value).all()

    return render_template(
        'ativos/form.html',
        fornecedores=fornecedores,
        contas_ativo=contas_ativo,
        tipos_ativo=TipoAtivo,
        bancos=bancos,
    )


@ativos_bp.route('/venda/<ativo_id>', methods=['GET', 'POST'])
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
                dt_primeiro = (
                    datetime.strptime(primeiro_venc, '%Y-%m-%d').date()
                    if primeiro_venc
                    else data_venda
                )
                AssetService.vender_ativo(
                    ativo.id,
                    comprador,
                    valor_venda,
                    data_venda,
                    num_parcelas,
                    dt_primeiro,
                )

            db.session.commit()
            flash('Venda registrada com sucesso! Titulos a receber gerados.', 'success')
            return redirect(_get_redirect_destino('ativos.lista'))
        except Exception as e:
            db.session.rollback()
            flash(f"Erro ao registrar venda: {str(e)}", "error")

    from datetime import date

    return render_template(
        'ativos/venda_form.html',
        ativo=ativo,
        compradores=_listar_compradores_ativos(),
        today=date.today(),
        next_url=request.values.get('next_url'),
    )


@ativos_bp.route('/recompra/<ativo_id>', methods=['GET', 'POST'])
def recompra(ativo_id):
    ativo = db.session.get(Ativo, ativo_id)
    if request.method == 'POST':
        try:
            quantidade = float(request.form.get('quantidade'))
            valor_unitario = Decimal(request.form.get('valor_unitario'))
            banco_id = request.form.get('banco_ativo_id')
            data_acq = datetime.strptime(request.form.get('data_aquisicao'), '%Y-%m-%d').date()

            AssetService.recomprar_investimento(ativo.id, valor_unitario, quantidade, data_acq, banco_id)
            db.session.commit()
            flash('Aporte/Recompra realizado com sucesso!', 'success')
            return redirect(_get_redirect_destino('ativos.lista'))
        except Exception as e:
            db.session.rollback()
            flash(f"Erro ao registrar recompra: {str(e)}", "error")

    from datetime import date

    bancos = Ativo.query.filter(Ativo.tipo == TipoAtivo.BANCO.value).all()
    return render_template(
        'ativos/recompra_form.html',
        ativo=ativo,
        bancos=bancos,
        today=date.today(),
        next_url=request.values.get('next_url'),
    )


@ativos_bp.route('/estornar/<ativo_id>')
def estornar(ativo_id):
    success, message = AssetService.estornar_compra_ativo(ativo_id)
    if success:
        flash(message, 'success')
        db.session.commit()
    else:
        flash(message, 'danger')
        db.session.rollback()

    return redirect(_get_redirect_destino('ativos.lista'))
