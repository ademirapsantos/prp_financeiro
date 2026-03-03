import csv
import io
from datetime import datetime

from flask import Blueprint, flash, redirect, render_template, request, send_file, url_for
from sqlalchemy.exc import IntegrityError

from .models import ContaContabil, NaturezaConta, TipoConta, db

contas_bp = Blueprint('contas', __name__, url_prefix='/contas')

CSV_COLUMNS = ['codigo', 'nome', 'tipo', 'natureza', 'parent_codigo']


def _enum_values(enum_cls):
    return {item.value for item in enum_cls}


def _parent_codigo_from_codigo(codigo):
    if not codigo or '.' not in codigo:
        return ''
    return codigo.rsplit('.', 1)[0]


def _normalize_csv_value(value):
    return (value or '').strip()


def _parse_csv_rows(file_storage):
    if not file_storage or not file_storage.filename:
        raise ValueError('Nenhum arquivo CSV foi enviado.')

    raw_bytes = file_storage.read()
    if not raw_bytes:
        raise ValueError('O arquivo CSV esta vazio.')

    try:
        raw_text = raw_bytes.decode('utf-8-sig')
    except UnicodeDecodeError:
        raw_text = raw_bytes.decode('latin-1')

    sample = raw_text[:2048]
    delimiter = ';' if sample.count(';') > sample.count(',') else ','
    reader = csv.DictReader(io.StringIO(raw_text), delimiter=delimiter)

    if not reader.fieldnames:
        raise ValueError('Nao foi possivel identificar o cabecalho do CSV.')

    fieldnames = {_normalize_csv_value(name) for name in reader.fieldnames if name}
    missing = [column for column in CSV_COLUMNS if column not in fieldnames]
    if missing:
        raise ValueError(f"CSV invalido. Colunas obrigatorias ausentes: {', '.join(missing)}.")

    rows = []
    for line_number, row in enumerate(reader, start=2):
        normalized = {
            _normalize_csv_value(key): _normalize_csv_value(value)
            for key, value in row.items() if key is not None
        }
        if not any(normalized.values()):
            continue
        normalized['_line_number'] = line_number
        rows.append(normalized)

    return rows


def _validate_import_row(row, existing_codes, batch_codes):
    codigo = row.get('codigo', '')
    nome = row.get('nome', '')
    tipo = row.get('tipo', '')
    natureza = row.get('natureza', '')
    parent_codigo = row.get('parent_codigo', '') or _parent_codigo_from_codigo(codigo)

    if not codigo or not nome or not tipo or not natureza:
        return False, 'Campos obrigatorios ausentes.', parent_codigo
    if tipo not in _enum_values(TipoConta):
        return False, f"Tipo invalido: {tipo}.", parent_codigo
    if natureza not in _enum_values(NaturezaConta):
        return False, f"Natureza invalida: {natureza}.", parent_codigo
    if codigo in batch_codes:
        return False, f"Codigo duplicado no arquivo: {codigo}.", parent_codigo
    if codigo in existing_codes:
        return None, f"Codigo ja existente: {codigo}.", parent_codigo
    if parent_codigo and parent_codigo == codigo:
        return False, 'A conta nao pode ser pai dela mesma.', parent_codigo
    return True, '', parent_codigo


def _import_contas_from_rows(rows):
    existing_codes = {conta.codigo for conta in ContaContabil.query.order_by(ContaContabil.codigo).all()}
    created_by_code = {}
    batch_codes = set()
    imported = 0
    ignored = 0
    errors = []

    sorted_rows = sorted(
        rows,
        key=lambda row: (
            len(_normalize_csv_value(row.get('codigo', '')).split('.')),
            _normalize_csv_value(row.get('codigo', ''))
        )
    )

    for row in sorted_rows:
        is_valid, message, parent_codigo = _validate_import_row(row, existing_codes, batch_codes)
        line_number = row.get('_line_number', '?')

        if is_valid is None:
            ignored += 1
            continue
        if is_valid is False:
            errors.append(f"Linha {line_number}: {message}")
            continue

        parent_id = None
        if parent_codigo:
            parent = created_by_code.get(parent_codigo)
            if not parent:
                parent = ContaContabil.query.filter_by(codigo=parent_codigo).first()
            if not parent:
                errors.append(f"Linha {line_number}: conta pai {parent_codigo} nao encontrada.")
                continue
            parent_id = parent.id

        conta = ContaContabil(
            codigo=row['codigo'],
            nome=row['nome'],
            tipo=row['tipo'],
            natureza=row['natureza'],
            parent_id=parent_id
        )
        db.session.add(conta)
        db.session.flush()

        created_by_code[conta.codigo] = conta
        existing_codes.add(conta.codigo)
        batch_codes.add(conta.codigo)
        imported += 1

    return imported, ignored, errors


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

    return render_template(
        'contas/lista.html',
        contas=contas,
        tipos=TipoConta,
        naturezas=NaturezaConta,
        filtros={'codigo': codigo, 'tipo': tipo, 'natureza': natureza}
    )


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
            flash('Conta contabil criada com sucesso!', 'success')
            return redirect(url_for('contas.lista'))
        except IntegrityError:
            db.session.rollback()
            flash('Erro: ja existe uma conta cadastrada com este codigo.', 'error')
            contas_pai = ContaContabil.query.order_by(ContaContabil.codigo).all()
            return render_template(
                'contas/form.html',
                contas_pai=contas_pai,
                tipos=TipoConta,
                naturezas=NaturezaConta
            )

    contas_pai = ContaContabil.query.order_by(ContaContabil.codigo).all()
    return render_template(
        'contas/form.html',
        contas_pai=contas_pai,
        tipos=TipoConta,
        naturezas=NaturezaConta
    )


@contas_bp.route('/editar/<id>', methods=['GET', 'POST'])
def editar(id):
    conta = db.session.get(ContaContabil, id)
    if not conta:
        flash('Conta nao encontrada.', 'error')
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
            flash(f"Conta '{conta.nome}' atualizada com sucesso!", 'success')
            return redirect(url_for('contas.lista'))
        except IntegrityError:
            db.session.rollback()
            flash('Erro: este codigo ja esta em uso por outra conta.', 'error')
            contas_pai = ContaContabil.query.filter(ContaContabil.id != id).order_by(ContaContabil.codigo).all()
            return render_template(
                'contas/form.html',
                conta=conta,
                contas_pai=contas_pai,
                tipos=TipoConta,
                naturezas=NaturezaConta
            )

    contas_pai = ContaContabil.query.filter(ContaContabil.id != id).order_by(ContaContabil.codigo).all()
    return render_template(
        'contas/form.html',
        conta=conta,
        contas_pai=contas_pai,
        tipos=TipoConta,
        naturezas=NaturezaConta
    )


@contas_bp.route('/api/<id>')
def get_conta_api(id):
    conta = db.session.get(ContaContabil, id)
    if not conta:
        return {'error': 'Conta nao encontrada'}, 404

    return {
        'id': conta.id,
        'codigo': conta.codigo,
        'nome': conta.nome,
        'tipo': conta.tipo,
        'natureza': conta.natureza,
        'parent_id': conta.parent_id
    }


@contas_bp.route('/exportar')
def exportar_csv():
    contas = ContaContabil.query.order_by(ContaContabil.codigo).all()

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=CSV_COLUMNS, delimiter=';')
    writer.writeheader()

    for conta in contas:
        writer.writerow({
            'codigo': conta.codigo,
            'nome': conta.nome,
            'tipo': conta.tipo,
            'natureza': conta.natureza,
            'parent_codigo': conta.pai.codigo if conta.pai else ''
        })

    memory_file = io.BytesIO(output.getvalue().encode('utf-8-sig'))
    memory_file.seek(0)
    filename = f"plano_contas_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

    return send_file(
        memory_file,
        as_attachment=True,
        download_name=filename,
        mimetype='text/csv'
    )


@contas_bp.route('/importar', methods=['POST'])
def importar_csv():
    file = request.files.get('arquivo')

    try:
        rows = _parse_csv_rows(file)
        imported, ignored, errors = _import_contas_from_rows(rows)
        db.session.commit()

        if errors:
            flash(
                f'Importacao concluida com ressalvas. {imported} conta(s) incluida(s), {ignored} ignorada(s) e {len(errors)} linha(s) com erro. '
                + ' | '.join(errors[:5]),
                'warning'
            )
        else:
            flash(
                f'Importacao concluida. {imported} conta(s) incluida(s) e {ignored} registro(s) ignorado(s) por codigo ja existente.',
                'success'
            )
    except ValueError as exc:
        db.session.rollback()
        flash(str(exc), 'error')
    except Exception:
        db.session.rollback()
        flash('Erro ao importar CSV do plano de contas.', 'error')

    return redirect(url_for('contas.lista'))
