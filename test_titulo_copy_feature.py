from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from urllib.parse import urlencode

from flask import Flask

from app.routes_financeiro import _build_titulo_copy_defaults, _titulo_esta_pago, copiar_titulo
import app.routes_financeiro as routes_financeiro


def _fake_titulo(status='Pago', tipo='Receber'):
    return SimpleNamespace(
        id='titulo-1',
        entidade_id='ent-1',
        descricao='Servico mensal',
        valor=Decimal('123.45'),
        data_vencimento=date(2026, 2, 25),
        status=status,
        tipo=tipo,
    )


def _fake_url_for(endpoint, **kwargs):
    if endpoint == 'financeiro.titulos':
        return '/financeiro/titulos'
    if endpoint == 'financeiro.nova_venda':
        return '/financeiro/venda?' + urlencode(kwargs)
    if endpoint == 'financeiro.novo_pagamento':
        return '/financeiro/pagamento?' + urlencode(kwargs)
    return '/' + endpoint


def test_copy_defaults_keep_base_fields_only():
    defaults = _build_titulo_copy_defaults(_fake_titulo())
    assert defaults['copied_from_id'] == 'titulo-1'
    assert defaults['entidade_id'] == 'ent-1'
    assert defaults['descricao'] == 'Servico mensal'
    assert defaults['valor'] == '123.45'
    assert defaults['data_vencimento'] == '2026-02-25'
    assert 'status' not in defaults


def test_copy_status_guard_only_allows_paid():
    assert _titulo_esta_pago(_fake_titulo(status='Pago')) is True
    assert _titulo_esta_pago(_fake_titulo(status='PAGO')) is True
    assert _titulo_esta_pago(_fake_titulo(status='Aberto')) is False


def test_copy_route_blocks_non_paid(monkeypatch):
    app = Flask(__name__)
    app.secret_key = 'test'

    monkeypatch.setattr(routes_financeiro, 'url_for', _fake_url_for)
    monkeypatch.setattr(routes_financeiro.db.session, 'get', lambda model, _id: _fake_titulo(status='Aberto'))

    with app.test_request_context('/financeiro/titulos/titulo-1/copiar?next=/financeiro/titulos'):
        response = copiar_titulo('titulo-1')

    assert response.status_code == 302
    assert response.location.endswith('/financeiro/titulos')


def test_copy_route_redirects_paid_receber_to_prefilled_form(monkeypatch):
    app = Flask(__name__)
    app.secret_key = 'test'

    monkeypatch.setattr(routes_financeiro, 'url_for', _fake_url_for)
    monkeypatch.setattr(routes_financeiro.db.session, 'get', lambda model, _id: _fake_titulo(status='Pago', tipo='Receber'))

    with app.test_request_context('/financeiro/titulos/titulo-1/copiar?next=/financeiro/titulos'):
        response = copiar_titulo('titulo-1')

    assert response.status_code == 302
    assert '/financeiro/venda?' in response.location
    assert 'copied_from_id=titulo-1' in response.location
    assert 'data_vencimento=2026-02-25' in response.location


def test_copy_button_condition_exists_in_titulos_template():
    with open('app/templates/financeiro/titulos.html', 'r', encoding='utf-8') as f:
        content = f.read()

    assert "{% if t.status in ['Pago', 'PAGO'] %}" in content
    assert "url_for('financeiro.copiar_titulo'" in content
