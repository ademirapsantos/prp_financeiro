from datetime import datetime
from decimal import Decimal, InvalidOperation
from functools import wraps

from flask import Blueprint, current_app, g, request
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from sqlalchemy import extract

from .models import (
    Ativo,
    CartaoCredito,
    ContaContabil,
    Entidade,
    FaturaCartao,
    StatusTitulo,
    Titulo,
    TransacaoCartao,
    TransacaoFinanceira,
    TipoAtivo,
    TipoConta,
    TipoTransacao,
    User,
    db,
)
from .services import CreditCardService, FinancialService


mobile_bp = Blueprint("mobile", __name__, url_prefix="/api/mobile")

TOKEN_SALT = "mobile-auth-v1"
TOKEN_MAX_AGE_SECONDS = 60 * 60 * 24 * 7


def _serializer():
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"], salt=TOKEN_SALT)


def _success(data=None, message="ok", status_code=200):
    return {"status": "success", "message": message, "data": data or {}}, status_code


def _error(message, status_code=400, data=None):
    payload = {"status": "error", "message": message, "data": data or {}}
    return payload, status_code


def _issue_token(user):
    return _serializer().dumps({"uid": user.id, "email": user.email})


def _parse_token(token):
    try:
        return _serializer().loads(token, max_age=TOKEN_MAX_AGE_SECONDS)
    except SignatureExpired:
        return None
    except BadSignature:
        return None


def _mobile_auth_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return _error("Token de acesso nÃ£o informado.", 401)

        token = auth_header.split(" ", 1)[1].strip()
        payload = _parse_token(token)
        if not payload:
            return _error("Token invÃ¡lido ou expirado.", 401)

        user = User.query.get(payload.get("uid"))
        if not user:
            return _error("UsuÃ¡rio do token nÃ£o encontrado.", 401)

        g.mobile_user = user
        return fn(*args, **kwargs)

    return wrapper


def _parse_date(value, field_name):
    try:
        return datetime.strptime(value, "%Y-%m-%d")
    except Exception:
        raise ValueError(f"Campo '{field_name}' deve estar no formato YYYY-MM-DD.")


def _parse_decimal(value, field_name):
    try:
        dec = Decimal(str(value).replace(".", "").replace(",", "."))
    except (InvalidOperation, ValueError):
        raise ValueError(f"Campo '{field_name}' invÃ¡lido.")
    if dec <= 0:
        raise ValueError(f"Campo '{field_name}' deve ser maior que zero.")
    return dec


def _to_money(value):
    return float(value or 0)


@mobile_bp.route("/auth/login", methods=["POST"])
def mobile_login():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not email or not password:
        return _error("Informe email e senha.", 400)

    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        return _error("Credenciais invÃ¡lidas.", 401)

    token = _issue_token(user)
    return _success(
        {
            "access_token": token,
            "token_type": "Bearer",
            "expires_in": TOKEN_MAX_AGE_SECONDS,
            "user": {
                "id": user.id,
                "nome": user.nome,
                "email": user.email,
                "is_admin": bool(user.is_admin),
                "deve_alterar_senha": bool(user.deve_alterar_senha),
            },
        },
        message="Login efetuado com sucesso.",
    )


@mobile_bp.route("/dashboard", methods=["GET"])
@_mobile_auth_required
def mobile_dashboard():
    hoje = datetime.utcnow()
    ano = request.args.get("ano", hoje.year, type=int)
    mes = request.args.get("mes", hoje.month, type=int)

    total_pendente = (
        db.session.query(db.func.sum(FaturaCartao.total - db.func.coalesce(FaturaCartao.total_pago, 0)))
        .filter(
            FaturaCartao.situacao_pagamento != "paga",
            extract("year", FaturaCartao.data_vencimento) == ano,
            extract("month", FaturaCartao.data_vencimento) == mes,
        )
        .scalar()
        or 0
    )

    total_despesas_mes = (
        db.session.query(db.func.sum(Titulo.valor))
        .filter(
            Titulo.tipo == "Pagar",
            Titulo.status == StatusTitulo.ABERTO.value,
            extract("year", Titulo.data_vencimento) == ano,
            extract("month", Titulo.data_vencimento) == mes,
        )
        .scalar()
        or 0
    )

    titulos_top = (
        Titulo.query.filter(Titulo.status == StatusTitulo.ABERTO.value)
        .order_by(Titulo.data_vencimento.asc())
        .limit(5)
        .all()
    )
    faturas_top = (
        FaturaCartao.query.filter(FaturaCartao.situacao_pagamento != "paga")
        .order_by(FaturaCartao.data_vencimento.asc())
        .limit(5)
        .all()
    )

    proximos = []
    for t in titulos_top:
        proximos.append(
            {
                "tipo": "titulo",
                "id": t.id,
                "descricao": t.descricao,
                "vencimento": t.data_vencimento.strftime("%Y-%m-%d"),
                "valor": _to_money(t.valor),
            }
        )
    for f in faturas_top:
        pendente = (f.total or 0) - (f.total_pago or 0)
        proximos.append(
            {
                "tipo": "fatura",
                "id": f.id,
                "descricao": f"Fatura {f.cartao.nome} ({f.competencia})",
                "vencimento": f.data_vencimento.strftime("%Y-%m-%d"),
                "valor": _to_money(pendente),
            }
        )

    proximos = sorted(proximos, key=lambda x: x["vencimento"])[:5]

    return _success(
        {
            "resumo": {
                "total_pendente_cartoes": _to_money(total_pendente),
                "total_despesas_mes": _to_money(total_despesas_mes),
            },
            "competencia": {"ano": ano, "mes": mes},
            "proximos_vencimentos": proximos,
            "atalhos": [
                {"id": "add_compra", "label": "Adicionar compra"},
                {"id": "ver_faturas", "label": "Ver faturas"},
                {"id": "ver_dividas", "label": "Ver dÃ­vidas"},
            ],
        }
    )


@mobile_bp.route("/dashboard/despesas-mes-detalhe", methods=["GET"])
@_mobile_auth_required
def mobile_dashboard_despesas_mes_detalhe():
    hoje = datetime.utcnow()
    ano = request.args.get("ano", hoje.year, type=int)
    mes = request.args.get("mes", hoje.month, type=int)

    titulos = (
        Titulo.query
        .filter(
            Titulo.tipo == "Pagar",
            Titulo.status == StatusTitulo.ABERTO.value,
            extract("year", Titulo.data_vencimento) == ano,
            extract("month", Titulo.data_vencimento) == mes,
        )
        .order_by(Titulo.data_vencimento.asc())
        .all()
    )

    items = []
    total = 0
    for titulo in titulos:
        entidade_nome = titulo.entidade.nome if titulo.entidade else None
        descricao = (titulo.descricao or "") or "Titulo a pagar"
        descricao_visual = f"{descricao} ({entidade_nome})" if entidade_nome else descricao
        valor = _to_money(titulo.valor)
        total += valor
        items.append(
            {
                "id": titulo.id,
                "titulo_id": titulo.id,
                "descricao": descricao_visual,
                "descricao_base": descricao,
                "entidade": entidade_nome,
                "data": titulo.data_vencimento.strftime("%Y-%m-%d"),
                "valor": valor,
            }
        )

    current_app.logger.info(
        "Dashboard despesas detalhe: ano=%s mes=%s itens=%s total=%s",
        ano,
        mes,
        len(items),
        total,
    )
    return _success({"items": items, "total": total, "ano": ano, "mes": mes})


@mobile_bp.route("/lancamentos", methods=["GET"])
@_mobile_auth_required
def mobile_lancamentos():
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 20, type=int), 100)
    q = (request.args.get("q") or "").strip().lower()
    hoje = datetime.utcnow().date()

    rows = []

    for t in (
        Titulo.query.filter(
            Titulo.tipo == "Pagar",
            Titulo.status == StatusTitulo.ABERTO.value,
            Titulo.data_vencimento >= hoje,
        )
        .order_by(Titulo.data_vencimento.asc())
        .all()
    ):
        rows.append(
            {
                "id": t.id,
                "tipo": (t.tipo or "").lower(),
                "meio": "conta",
                "descricao": t.descricao,
                "valor": _to_money(t.valor),
                "data": t.data_vencimento.strftime("%Y-%m-%d"),
                "entidade": t.entidade.nome if t.entidade else None,
            }
        )

    if q:
        rows = [r for r in rows if q in (r.get("descricao") or "").lower()]

    rows = sorted(rows, key=lambda x: x["data"], reverse=True)
    total_items = len(rows)
    start = (page - 1) * per_page
    items = rows[start : start + per_page]

    return _success(
        {
            "items": items,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total_items": total_items,
                "total_pages": (total_items + per_page - 1) // per_page if total_items else 1,
            },
        }
    )


@mobile_bp.route("/lancamentos", methods=["POST"])
@_mobile_auth_required
def mobile_criar_lancamento():
    body = request.get_json(silent=True) or {}
    current_app.logger.info(
        "Mobile lancamento POST recebido: user_id=%s meio=%s campos=%s",
        getattr(g, "mobile_user", None).id if getattr(g, "mobile_user", None) else None,
        body.get("meio"),
        sorted(body.keys()),
    )
    allowed_fields = {
        "data",
        "valor",
        "descricao",
        "meio",
        "categoria_id",
        "cartao_id",
        "num_parcelas",
        "banco_id",
        "entidade_id",
        "tipo_movimentacao",
    }
    extra_fields = sorted(set(body.keys()) - allowed_fields)
    if extra_fields:
        current_app.logger.warning(
            "Mobile lancamento rejeitado (campos nao permitidos): user_id=%s invalid_fields=%s",
            getattr(g, "mobile_user", None).id if getattr(g, "mobile_user", None) else None,
            extra_fields,
        )
        return _error("Campos nÃ£o permitidos no payload.", 400, {"invalid_fields": extra_fields})

    try:
        valor = _parse_decimal(body.get("valor"), "valor")
        descricao = (body.get("descricao") or "").strip()
        meio = (body.get("meio") or "").strip().lower()

        if not descricao:
            raise ValueError("Campo 'descricao' Ã© obrigatÃ³rio.")
        if meio not in {"cartao", "conta"}:
            raise ValueError("Campo 'meio' deve ser 'cartao' ou 'conta'.")

        if meio == "cartao":
            # Para cartão, a data de compra no mobile sempre segue o momento do lançamento.
            data = datetime.utcnow()
            cartao_id = body.get("cartao_id")
            categoria_id = body.get("categoria_id")
            num_parcelas = int(body.get("num_parcelas", 1))
            if not cartao_id or not categoria_id:
                raise ValueError("Para meio='cartao', informe 'cartao_id' e 'categoria_id'.")

            cartao = CartaoCredito.query.get(cartao_id)
            if not cartao:
                raise ValueError("CartÃ£o nÃ£o encontrado.")

            transacao = CreditCardService.registrar_compra(
                cartao=cartao,
                descricao=descricao,
                valor=valor,
                categoria_id=categoria_id,
                data_compra=data,
                num_parcelas=num_parcelas,
            )
            db.session.commit()
            return _success(
                {
                    "id": transacao.id,
                    "meio": "cartao",
                    "fatura_id": transacao.fatura_id,
                    "data": transacao.data.strftime("%Y-%m-%d"),
                },
                message="LanÃ§amento de cartÃ£o criado com sucesso.",
                status_code=201,
            )

        entidade_id = body.get("entidade_id")
        tipo_mov = (body.get("tipo_movimentacao") or "pagar").strip().lower()
        data_raw = body.get("data")
        if not data_raw:
            raise ValueError("Para meio='conta', informe 'data'.")
        data = _parse_date(data_raw, "data")
        if not entidade_id:
            raise ValueError("Para meio='conta', informe 'entidade_id'.")

        entidade = Entidade.query.get(entidade_id)
        if not entidade:
            raise ValueError("Entidade nÃ£o encontrada.")

        if tipo_mov == "receber":
            titulo = FinancialService.criar_titulo_receber(
                entidade=entidade,
                descricao=descricao,
                valor=valor,
                data_vencimento=data,
            )
        else:
            titulo = FinancialService.criar_titulo_pagar(
                entidade=entidade,
                descricao=descricao,
                valor=valor,
                data_vencimento=data,
            )
        db.session.commit()
        return _success(
            {
                "id": titulo.id,
                "meio": "conta",
                "data_vencimento": titulo.data_vencimento.strftime("%Y-%m-%d"),
                "tipo": titulo.tipo,
                "status": titulo.status,
            },
            message="LanÃ§amento em conta criado com sucesso.",
            status_code=201,
        )

    except ValueError as ex:
        db.session.rollback()
        current_app.logger.warning(
            "Mobile lancamento rejeitado por validacao: user_id=%s erro=%s payload=%s",
            getattr(g, "mobile_user", None).id if getattr(g, "mobile_user", None) else None,
            str(ex),
            {
                "meio": body.get("meio"),
                "data": body.get("data"),
                "descricao": body.get("descricao"),
                "valor": body.get("valor"),
                "cartao_id": body.get("cartao_id"),
                "categoria_id": body.get("categoria_id"),
                "banco_id": body.get("banco_id"),
                "entidade_id": body.get("entidade_id"),
                "tipo_movimentacao": body.get("tipo_movimentacao"),
            },
        )
        return _error(str(ex), 400)
    except Exception as ex:
        db.session.rollback()
        current_app.logger.exception("Falha ao criar lancamento mobile")
        return _error(f"Erro ao criar lanÃ§amento: {str(ex)}", 500)


@mobile_bp.route("/lancamentos/meta", methods=["GET"])
@_mobile_auth_required
def mobile_lancamentos_meta():
    categorias = (
        ContaContabil.query.filter_by(tipo=TipoConta.DESPESA.value)
        .order_by(ContaContabil.codigo.asc())
        .all()
    )
    categorias = [c for c in categorias if c.is_analitica]
    bancos = Ativo.query.filter_by(tipo=TipoAtivo.BANCO.value).order_by(Ativo.descricao.asc()).all()
    entidades = Entidade.query.order_by(Entidade.nome.asc()).all()

    return _success(
        {
            "categorias_despesa": [
                {"id": c.id, "codigo": c.codigo, "nome": c.nome} for c in categorias
            ],
            "bancos": [{"id": b.id, "nome": b.descricao} for b in bancos],
            "entidades": [
                {
                    "id": e.id,
                    "nome": e.nome,
                    "tipo": e.tipo,
                    # Regras para criação de títulos no mobile:
                    # pagar -> criar_titulo_pagar
                    # receber -> criar_titulo_receber
                    "suporta_pagar": bool(e.conta_resultado_id or e.conta_compra_id),
                    "suporta_receber": bool(e.conta_resultado_id or e.conta_venda_id),
                }
                for e in entidades
            ],
        }
    )


@mobile_bp.route("/cartoes", methods=["GET"])
@_mobile_auth_required
def mobile_cartoes():
    cartoes = CartaoCredito.query.filter_by(ativo=True).order_by(CartaoCredito.nome.asc()).all()
    data = []
    for c in cartoes:
        data.append(
            {
                "id": c.id,
                "nome": c.nome,
                "bandeira": c.bandeira,
                "banco": c.banco.descricao if c.banco else None,
                "limite_total": _to_money(c.limite_total),
                "limite_disponivel": _to_money(c.limite_disponivel),
                "dia_fechamento": c.dia_fechamento,
                "dia_vencimento": c.dia_vencimento,
            }
        )
    return _success({"items": data})


@mobile_bp.route("/faturas", methods=["GET"])
@_mobile_auth_required
def mobile_faturas():
    status = (request.args.get("status") or "aberta").strip().lower()
    mes = (request.args.get("mes") or "").strip()
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 20, type=int), 100)

    query = FaturaCartao.query
    if status == "aberta":
        query = query.filter(FaturaCartao.situacao_pagamento != "paga")
    if mes:
        query = query.filter(FaturaCartao.competencia == mes)

    pagination = query.order_by(FaturaCartao.data_vencimento.desc()).paginate(page=page, per_page=per_page, error_out=False)

    items = []
    for f in pagination.items:
        pendente = (f.total or 0) - (f.total_pago or 0)
        items.append(
            {
                "id": f.id,
                "cartao_id": f.card_id,
                "cartao_nome": f.cartao.nome if f.cartao else None,
                "competencia": f.competencia,
                "status_ciclo": f.status,
                "situacao_pagamento": f.situacao_pagamento,
                "data_vencimento": f.data_vencimento.strftime("%Y-%m-%d"),
                "total": _to_money(f.total),
                "total_pago": _to_money(f.total_pago),
                "pendente": _to_money(pendente),
            }
        )

    return _success(
        {
            "items": items,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total_items": pagination.total,
                "total_pages": pagination.pages or 1,
            },
        }
    )


@mobile_bp.route("/faturas/<fatura_id>", methods=["GET"])
@_mobile_auth_required
def mobile_fatura_detalhe(fatura_id):
    fatura = FaturaCartao.query.get_or_404(fatura_id)
    pendente = (fatura.total or 0) - (fatura.total_pago or 0)
    transacoes = []
    for tr in (
        TransacaoCartao.query.filter_by(fatura_id=fatura.id).order_by(TransacaoCartao.data.desc()).all()
    ):
        transacoes.append(
            {
                "id": tr.id,
                "descricao": tr.descricao,
                "data": tr.data.strftime("%Y-%m-%d"),
                "valor": _to_money(tr.valor),
                "status": tr.status,
                "categoria": tr.categoria.nome if tr.categoria else None,
            }
        )

    return _success(
        {
            "id": fatura.id,
            "cartao": {"id": fatura.card_id, "nome": fatura.cartao.nome if fatura.cartao else None},
            "competencia": fatura.competencia,
            "status_ciclo": fatura.status,
            "situacao_pagamento": fatura.situacao_pagamento,
            "data_fechamento": fatura.data_fechamento.strftime("%Y-%m-%d"),
            "data_vencimento": fatura.data_vencimento.strftime("%Y-%m-%d"),
            "total": _to_money(fatura.total),
            "total_pago": _to_money(fatura.total_pago),
            "pendente": _to_money(pendente),
            "itens": transacoes,
        }
    )


@mobile_bp.route("/titulos", methods=["GET"])
@_mobile_auth_required
def mobile_titulos():
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 20, type=int), 100)
    hoje = datetime.utcnow().date()

    query = Titulo.query.filter(
        Titulo.tipo == "Pagar",
        Titulo.status == StatusTitulo.ABERTO.value,
        Titulo.data_vencimento < hoje,
    )

    pagination = query.order_by(Titulo.data_vencimento.asc()).paginate(page=page, per_page=per_page, error_out=False)
    items = []
    for t in pagination.items:
        items.append(
            {
                "id": t.id,
                "descricao": t.descricao,
                "tipo": t.tipo,
                "status": t.status,
                "valor": _to_money(t.valor),
                "data_vencimento": t.data_vencimento.strftime("%Y-%m-%d"),
                "entidade": t.entidade.nome if t.entidade else None,
            }
        )

    return _success(
        {
            "items": items,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total_items": pagination.total,
                "total_pages": pagination.pages or 1,
            },
        }
    )


@mobile_bp.route("/titulos/<titulo_id>", methods=["GET"])
@_mobile_auth_required
def mobile_titulo_detalhe(titulo_id):
    t = Titulo.query.get_or_404(titulo_id)
    return _success(
        {
            "id": t.id,
            "descricao": t.descricao,
            "tipo": t.tipo,
            "status": t.status,
            "valor": _to_money(t.valor),
            "data_vencimento": t.data_vencimento.strftime("%Y-%m-%d"),
            "data_emissao": t.data_emissao.strftime("%Y-%m-%d") if t.data_emissao else None,
            "entidade": {
                "id": t.entidade.id if t.entidade else None,
                "nome": t.entidade.nome if t.entidade else None,
                "tipo": t.entidade.tipo if t.entidade else None,
            },
            "parcela": {"atual": t.parcela_atual, "total": t.total_parcelas},
        }
    )
