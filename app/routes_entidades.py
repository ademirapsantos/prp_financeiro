from flask import Blueprint, render_template, request, redirect, url_for, flash
from .models import Entidade, TipoEntidade, ContaContabil, db

entidades_bp = Blueprint('entidades', __name__, url_prefix='/entidades')

@entidades_bp.route('/')
def lista():
    page = request.args.get('page', 1, type=int)
    per_page = 50
    nome = request.args.get('nome', '')
    tipo = request.args.get('tipo', '')
    
    query = Entidade.query
    
    if nome:
        query = query.filter(Entidade.nome.ilike(f"%{nome}%"))
    
    if tipo:
        query = query.filter(Entidade.tipo == tipo)
        
    pagination = query.order_by(Entidade.nome).paginate(page=page, per_page=per_page, error_out=False)
    entidades = pagination.items
    
    return render_template('entidades/lista.html', 
                         entidades=entidades, 
                         pagination=pagination,
                         filtros={'nome': nome, 'tipo': tipo},
                         tipos_entidade=TipoEntidade)

@entidades_bp.route('/nova', methods=['GET', 'POST'])
def nova():
    if request.method == 'POST':
        nome = request.form.get('nome')
        tipo = request.form.get('tipo')
        doc = request.form.get('documento')
        
        c_id = None
        r_id = None
        v_id = None
        p_id = None

        if tipo == 'Fornecedor':
            p_id = request.form.get('conta_compra_id_forn')
        elif tipo == 'Cliente':
            v_id = request.form.get('conta_venda_id_cli')
        elif tipo == 'Outros':
            p_id = request.form.get('conta_compra_id_out')
            v_id = request.form.get('conta_venda_id_out')

        nova_entidade = Entidade(
            nome=nome,
            tipo=tipo,
            documento=doc,
            conta_contabil_id=c_id if c_id else None,
            conta_resultado_id=r_id if r_id else None,
            conta_venda_id=v_id if v_id else None,
            conta_compra_id=p_id if p_id else None
        )
        db.session.add(nova_entidade)
        db.session.commit()
        flash('Entidade cadastrada com sucesso!', 'success')
        return redirect(url_for('entidades.lista'))
    
    contas = ContaContabil.query.order_by(ContaContabil.codigo).all()
    return render_template('entidades/form.html', contas=contas)

@entidades_bp.route('/editar/<id>', methods=['GET', 'POST'])
def editar(id):
    entidade = db.session.get(Entidade, id)
    if not entidade:
        flash('Entidade não encontrada.', 'error')
        return redirect(url_for('entidades.lista'))
    
    if request.method == 'POST':
        entidade.nome = request.form.get('nome')
        entidade.tipo = request.form.get('tipo')
        entidade.documento = request.form.get('documento')
        
        entidade.conta_contabil_id = None
        entidade.conta_resultado_id = None
        entidade.conta_venda_id = None
        entidade.conta_compra_id = None

        if entidade.tipo == 'Fornecedor':
            entidade.conta_compra_id = request.form.get('conta_compra_id_forn')
        elif entidade.tipo == 'Cliente':
            entidade.conta_venda_id = request.form.get('conta_venda_id_cli')
        elif entidade.tipo == 'Outros':
            entidade.conta_compra_id = request.form.get('conta_compra_id_out')
            entidade.conta_venda_id = request.form.get('conta_venda_id_out')
        
        db.session.commit()
        flash(f"Entidade '{entidade.nome}' atualizada com sucesso!", "success")
        return redirect(url_for('entidades.lista'))
    
    contas = ContaContabil.query.order_by(ContaContabil.codigo).all()
    return render_template('entidades/form.html', entidade=entidade, contas=contas)
