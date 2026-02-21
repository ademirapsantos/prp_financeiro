from flask import Blueprint, render_template, request, redirect, url_for, flash
from sqlalchemy.exc import IntegrityError
from .models import ContaContabil, TipoConta, NaturezaConta, db

contas_bp = Blueprint('contas', __name__, url_prefix='/contas')

@contas_bp.route('/')
def lista():
    codigo = request.args.get('codigo', '')
    tipo = request.args.get('tipo', '')
    natureza = request.args.get('natureza', '')

    query = ContaContabil.query

    if codigo:
        query = query.filter(ContaContabil.codigo.like(f"{codigo}%"))
    if tipo:
        query = query.filter(ContaContabil.tipo == tipo)
    if natureza:
        query = query.filter(ContaContabil.natureza == natureza)

    contas = query.order_by(ContaContabil.codigo).all()
    
    return render_template('contas/lista.html', 
                         contas=contas, 
                         tipos=TipoConta, 
                         naturezas=NaturezaConta,
                         filtros={'codigo': codigo, 'tipo': tipo, 'natureza': natureza})

@contas_bp.route('/nova', methods=['GET', 'POST'])
def nova():
    if request.method == 'POST':
        codigo = request.form.get('codigo')
        nome = request.form.get('nome')
        tipo = request.form.get('tipo')
        natureza = request.form.get('natureza')
        parent_id = request.form.get('parent_id')

        nova_conta = ContaContabil(
            codigo=codigo,
            nome=nome,
            tipo=tipo,
            natureza=natureza,
            parent_id=parent_id if parent_id else None
        )
        try:
            db.session.add(nova_conta)
            db.session.commit()
            flash('Conta contábil criada com sucesso!', 'success')
            return redirect(url_for('contas.lista'))
        except IntegrityError:
            db.session.rollback()
            flash('Erro: Já existe uma conta cadastrada com este código.', 'error')
            # Recarregar formulário com os dados enviados
            contas_pai = ContaContabil.query.order_by(ContaContabil.codigo).all()
            return render_template('contas/form.html', 
                                 contas_pai=contas_pai, 
                                 tipos=TipoConta, 
                                 naturezas=NaturezaConta)

    contas_pai = ContaContabil.query.order_by(ContaContabil.codigo).all()
    return render_template('contas/form.html', 
                         contas_pai=contas_pai, 
                         tipos=TipoConta, 
                         naturezas=NaturezaConta)

@contas_bp.route('/editar/<id>', methods=['GET', 'POST'])
def editar(id):
    conta = db.session.get(ContaContabil, id)
    if not conta:
        flash('Conta não encontrada.', 'error')
        return redirect(url_for('contas.lista'))

    if request.method == 'POST':
        conta.codigo = request.form.get('codigo')
        conta.nome = request.form.get('nome')
        conta.tipo = request.form.get('tipo')
        conta.natureza = request.form.get('natureza')
        
        parent_id = request.form.get('parent_id')
        conta.parent_id = parent_id if parent_id else None

        try:
            db.session.commit()
            flash(f"Conta '{conta.nome}' atualizada com sucesso!", "success")
            return redirect(url_for('contas.lista'))
        except IntegrityError:
            db.session.rollback()
            flash('Erro: Este código já está em uso por outra conta.', 'error')
            contas_pai = ContaContabil.query.filter(ContaContabil.id != id).order_by(ContaContabil.codigo).all()
            return render_template('contas/form.html', 
                                 conta=conta, 
                                 contas_pai=contas_pai, 
                                 tipos=TipoConta, 
                                 naturezas=NaturezaConta)

    contas_pai = ContaContabil.query.filter(ContaContabil.id != id).order_by(ContaContabil.codigo).all()
    return render_template('contas/form.html', 
                         conta=conta, 
                         contas_pai=contas_pai, 
                         tipos=TipoConta, 
                         naturezas=NaturezaConta)
@contas_bp.route('/api/<id>')
def get_conta_api(id):
    conta = db.session.get(ContaContabil, id)
    if not conta:
        return {'error': 'Conta não encontrada'}, 404
    
    return {
        'id': conta.id,
        'codigo': conta.codigo,
        'nome': conta.nome,
        'tipo': conta.tipo,
        'natureza': conta.natureza,
        'parent_id': conta.parent_id
    }
