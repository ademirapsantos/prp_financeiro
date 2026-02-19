from . import db
from datetime import datetime
from sqlalchemy import Enum as EnumType
import enum
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

# --- Módulo de Autenticação ---

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    deve_alterar_senha = db.Column(db.Boolean, default=True) # Força troca no primeiro login
    is_admin = db.Column(db.Boolean, default=False)
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)
    tema = db.Column(db.String(10), default='light') # 'light' ou 'dark'

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"<User {self.email}>"


# Enums para tipagem forte
class TipoConta(enum.Enum):
    ATIVO = "Ativo"
    PASSIVO = "Passivo"
    RECEITA = "Receita"
    DESPESA = "Despesa"
    PATRIMONIO_LIQUIDO = "Patrimônio Líquido"

class NaturezaConta(enum.Enum):
    DEVEDORA = "Devedora"
    CREDORA = "Credora"

class TipoEntidade(enum.Enum):
    CLIENTE = "Cliente"
    FORNECEDOR = "Fornecedor"
    OUTROS = "Outros"

class TipoAtivo(enum.Enum):
    BANCO = "Banco"
    IMOVEL = "Imovel"
    VEICULO = "Veiculo"
    INVESTIMENTO = "Investimento"
    OUTROS = "Outros"

class StatusTitulo(enum.Enum):
    ABERTO = "Aberto"
    PAGO = "Pago"
    CANCELADO = "Cancelado"

class TipoTitulo(enum.Enum):
    PAGAR = "Pagar"
    RECEBER = "Receber"

class TipoTransacao(enum.Enum):
    PAGAMENTO = "Pagamento"
    RECEBIMENTO = "Recebimento"
    TRANSFERENCIA = "Transferencia"
    AQUISICAO = "Aquisicao"

# --- Módulo Contábil ---

class ContaContabil(db.Model):
    __tablename__ = 'contas_contabeis'
    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(20), unique=True, nullable=False) # Ex: 1.1.01
    nome = db.Column(db.String(100), nullable=False)
    tipo = db.Column(db.String(50), nullable=False)
    natureza = db.Column(db.String(20), nullable=False)
    
    # Hierarquia
    parent_id = db.Column(db.Integer, db.ForeignKey('contas_contabeis.id'), nullable=True)
    subcontas = db.relationship('ContaContabil', backref=db.backref('pai', remote_side=[id]), lazy='dynamic')

    # Relacionamentos
    partidas = db.relationship('PartidaDiario', backref='conta', lazy=True)

    @property
    def is_analitica(self):
        return self.subcontas.count() == 0

    def __repr__(self):
        return f"<Conta {self.codigo} - {self.nome}>"

class LivroDiario(db.Model):
    __tablename__ = 'livro_diario'
    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    historico = db.Column(db.String(255), nullable=False)
    transacao_id = db.Column(db.Integer, db.ForeignKey('transacoes_financeiras.id'), nullable=True)
    
    # Relação com os itens (partidas)
    partidas = db.relationship('PartidaDiario', backref='diario', lazy=True, cascade="all, delete-orphan")

class PartidaDiario(db.Model):
    __tablename__ = 'partidas_diario'
    id = db.Column(db.Integer, primary_key=True)
    diario_id = db.Column(db.Integer, db.ForeignKey('livro_diario.id'), nullable=False)
    conta_id = db.Column(db.Integer, db.ForeignKey('contas_contabeis.id'), nullable=False)
    tipo = db.Column(db.String(1), nullable=False) # 'D' para Débito, 'C' para Crédito
    valor = db.Column(db.Numeric(10, 2), nullable=False)

# --- Módulo de Parceiros e Ativos ---

class Entidade(db.Model):
    __tablename__ = 'entidades'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    tipo = db.Column(db.String(20), nullable=False)
    documento = db.Column(db.String(20), nullable=True)
    # Conta contábil padrão (Ex: Fornecedores a Pagar ou Clientes a Receber - Balanço)
    conta_contabil_id = db.Column(db.Integer, db.ForeignKey('contas_contabeis.id'), nullable=True)
    
    # Conta de Resultado padrão (Ex: Vendas para Clientes, Despesa X para Fornecedores)
    conta_resultado_id = db.Column(db.Integer, db.ForeignKey('contas_contabeis.id'), nullable=True)

    # Conta contábil de Venda (Ativo - Clientes a Receber) - Usado no tipo 'Outros'
    conta_venda_id = db.Column(db.Integer, db.ForeignKey('contas_contabeis.id'), nullable=True)
    # Conta contábil de Compra (Passivo/Despesa - Contas a Pagar) - Usado no tipo 'Outros'
    conta_compra_id = db.Column(db.Integer, db.ForeignKey('contas_contabeis.id'), nullable=True)
    
    conta_contabil = db.relationship('ContaContabil', foreign_keys=[conta_contabil_id], backref='entidades_patrimonial')
    conta_resultado = db.relationship('ContaContabil', foreign_keys=[conta_resultado_id], backref='entidades_resultado')
    conta_venda = db.relationship('ContaContabil', foreign_keys=[conta_venda_id], backref='entidades_venda')
    conta_compra = db.relationship('ContaContabil', foreign_keys=[conta_compra_id], backref='entidades_compra')
    
    titulos = db.relationship('Titulo', backref='entidade', lazy=True)

class Ativo(db.Model):
    __tablename__ = 'ativos'
    id = db.Column(db.Integer, primary_key=True)
    descricao = db.Column(db.String(100), nullable=False)
    tipo = db.Column(db.String(20), nullable=False)
    numero_conta = db.Column(db.String(30), nullable=True)
    valor_atual = db.Column(db.Numeric(10, 2), default=0.0)
    data_aquisicao = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    
    # Conta contábil que representa este ativo no Balanço (Ex: Banco X, Veículo Y)
    conta_contabil_id = db.Column(db.Integer, db.ForeignKey('contas_contabeis.id'), nullable=True)
    conta_contabil = db.relationship('ContaContabil', backref='ativos')
    
    # Controle de Investimentos / Qtd
    quantidade = db.Column(db.Float, default=0.0)
    valor_unitario = db.Column(db.Numeric(10, 2), default=0.0)
    
    transacoes = db.relationship('TransacaoFinanceira', backref='ativo', lazy=True)

# --- Módulo Financeiro ---

class Titulo(db.Model):
    __tablename__ = 'titulos'
    id = db.Column(db.Integer, primary_key=True)
    entidade_id = db.Column(db.Integer, db.ForeignKey('entidades.id'), nullable=False)
    descricao = db.Column(db.String(100), nullable=False)
    valor = db.Column(db.Numeric(10, 2), nullable=False)
    data_vencimento = db.Column(db.Date, nullable=False)
    data_emissao = db.Column(db.Date, default=datetime.utcnow)
    status = db.Column(db.String(20), default=StatusTitulo.ABERTO.value)
    tipo = db.Column(db.String(20), nullable=False)
    
    # Controle de Parcelamento
    parcela_atual = db.Column(db.Integer, nullable=True)
    total_parcelas = db.Column(db.Integer, nullable=True)
    ativo_id = db.Column(db.Integer, db.ForeignKey('ativos.id'), nullable=True)
    
    ativo = db.relationship('Ativo', backref='titulos_financeiros')
    transacoes = db.relationship('TransacaoFinanceira', backref='titulo', lazy=True)

    @property
    def data_liquidacao(self):
        """Retorna a data da transação de liquidação mais recente."""
        if self.status not in ['Pago', 'PAGO']:
            return None
        
        # Busca a transação de pagamento/recebimento mais recente
        ultima_transacao = TransacaoFinanceira.query.filter_by(titulo_id=self.id)\
            .order_by(TransacaoFinanceira.data.desc()).first()
        
        return ultima_transacao.data.date() if ultima_transacao else None

class TransacaoFinanceira(db.Model):
    __tablename__ = 'transacoes_financeiras'
    id = db.Column(db.Integer, primary_key=True)
    titulo_id = db.Column(db.Integer, db.ForeignKey('titulos.id'), nullable=True) # Pode ser nulo (ex: transferencia)
    ativo_id = db.Column(db.Integer, db.ForeignKey('ativos.id'), nullable=True) # Banco envolvido
    tipo = db.Column(db.String(20), nullable=False)
    valor = db.Column(db.Numeric(10, 2), nullable=False)
    valor_bruto = db.Column(db.Numeric(10, 2), nullable=True)
    valor_desconto = db.Column(db.Numeric(10, 2), default=0.0)
    valor_liquido = db.Column(db.Numeric(10, 2), default=0.0)
    data = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Link reverso para o diário contábil gerado
    lancamentos_contabeis = db.relationship('LivroDiario', backref='transacao_origem', lazy=True)

class Configuracao(db.Model):
    __tablename__ = 'configuracoes'
    id = db.Column(db.Integer, primary_key=True)
    chave = db.Column(db.String(50), unique=True, nullable=False)
    valor = db.Column(db.Text, nullable=True)
    descricao = db.Column(db.String(255), nullable=True)

    @staticmethod
    def get_valor(chave, default=None):
        config = Configuracao.query.filter_by(chave=chave).first()
        return config.valor if config else default

    @staticmethod
    def set_valor(chave, valor, descricao=None):
        config = Configuracao.query.filter_by(chave=chave).first()
        if config:
            config.valor = valor
            if descricao:
                config.descricao = descricao
        else:
            config = Configuracao(chave=chave, valor=valor, descricao=descricao)
            db.session.add(config)
        db.session.commit()

class ConfiguracaoSMTP(db.Model):
    __tablename__ = 'configuracao_smtp'
    id = db.Column(db.Integer, primary_key=True)
    smtp_server = db.Column(db.String(100), nullable=False, default='smtp.gmail.com')
    smtp_port = db.Column(db.Integer, nullable=False, default=587)
    smtp_user = db.Column(db.String(100), nullable=True)
    smtp_password = db.Column(db.String(100), nullable=True)
    use_tls = db.Column(db.Boolean, default=True)
    use_ssl = db.Column(db.Boolean, default=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<ConfiguracaoSMTP {self.smtp_server}>"

# --- Módulo de Cartão de Crédito ---

class CartaoCredito(db.Model):
    __tablename__ = 'cartoes_credito'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    banco_id = db.Column(db.Integer, db.ForeignKey('ativos.id'), nullable=True) # Vinculado a um banco (Ativo)
    nome = db.Column(db.String(100), nullable=False)
    bandeira = db.Column(db.String(50))
    limite_total = db.Column(db.Numeric(10, 2), default=0.0)
    dia_fechamento = db.Column(db.Integer, nullable=False) # Dia do mês
    dia_vencimento = db.Column(db.Integer, nullable=False) # Dia do mês
    limite_disponivel = db.Column(db.Numeric(10, 2)) # Cache do saldo atual
    
    # Limite Emergencial
    perc_limite_emergencial = db.Column(db.Numeric(5, 2), default=0.0) # ex: 0.35 para 35%
    limite_emergencial_ativo = db.Column(db.Boolean, default=False)
    
    conta_contabil_id = db.Column(db.Integer, db.ForeignKey('contas_contabeis.id'), nullable=False) # Passivo
    ativo = db.Column(db.Boolean, default=True)

    # Relationships
    banco = db.relationship('Ativo', backref='cartoes')
    conta_contabil = db.relationship('ContaContabil', backref='cartao_passivo')
    transacoes = db.relationship('TransacaoCartao', order_by='TransacaoCartao.data.desc()', backref='cartao', lazy=True)
    faturas = db.relationship('FaturaCartao', order_by='FaturaCartao.competencia.desc()', backref='cartao', lazy=True)

    @property
    def limite_maximo_total(self):
        from decimal import Decimal
        if self.limite_emergencial_ativo and self.perc_limite_emergencial > 0:
            return self.limite_total * (Decimal('1.0') + Decimal(str(self.perc_limite_emergencial)))
        return self.limite_total

class TransacaoCartao(db.Model):
    __tablename__ = 'transacoes_cartao'
    id = db.Column(db.Integer, primary_key=True)
    card_id = db.Column(db.Integer, db.ForeignKey('cartoes_credito.id'), nullable=False)
    data = db.Column(db.DateTime, default=datetime.utcnow)
    descricao = db.Column(db.String(255), nullable=False)
    valor = db.Column(db.Numeric(10, 2), nullable=False)
    categoria_id = db.Column(db.Integer, db.ForeignKey('contas_contabeis.id'), nullable=True) # Pra despesa
    fatura_id = db.Column(db.Integer, db.ForeignKey('faturas_cartao.id'), nullable=True) # Será obrigatório após migração
    competencia_calculada = db.Column(db.String(7), nullable=True) # YYYY-MM redundante para consulta
    transacao_financeira_id = db.Column(db.Integer, db.ForeignKey('transacoes_financeiras.id'), nullable=True) # Link contábil
    status = db.Column(db.String(20), default='confirmada') # pendente/confirmada/estornada
    
    # Parcelamento (Opção B: controle gerencial)
    installment_group_id = db.Column(db.String(50), nullable=True)
    installment_n = db.Column(db.Integer, nullable=True)
    installment_total = db.Column(db.Integer, nullable=True)

    categoria = db.relationship('ContaContabil', foreign_keys=[categoria_id])
    fatura = db.relationship('FaturaCartao', backref='transacoes_list')
    transacao_contabil = db.relationship('TransacaoFinanceira', backref='transacao_cartao')

class FaturaCartao(db.Model):
    __tablename__ = 'faturas_cartao'
    id = db.Column(db.Integer, primary_key=True)
    card_id = db.Column(db.Integer, db.ForeignKey('cartoes_credito.id'), nullable=False)
    competencia = db.Column(db.String(7), nullable=False) # ex: 2026-02
    data_fechamento = db.Column(db.Date, nullable=False)
    data_vencimento = db.Column(db.Date, nullable=False)
    total = db.Column(db.Numeric(10, 2), default=0.0)
    total_pago = db.Column(db.Numeric(10, 2), default=0.0)
    data_pagamento_ultima = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(20), default='aberta') # aberta/fechada (ciclo)
    situacao_pagamento = db.Column(db.String(20), default='em_aberto') # em_aberto/parcial/paga (financeiro)

    # Relationships
    pagamentos = db.relationship('PagamentoFaturaCartao', backref='fatura', lazy=True)

class PagamentoFaturaCartao(db.Model):
    __tablename__ = 'pagamentos_fatura_cartao'
    id = db.Column(db.Integer, primary_key=True)
    fatura_id = db.Column(db.Integer, db.ForeignKey('faturas_cartao.id'), nullable=False)
    banco_id = db.Column(db.Integer, db.ForeignKey('ativos.id'), nullable=True)
    valor = db.Column(db.Numeric(10, 2), nullable=False) # Principal
    valor_encargos = db.Column(db.Numeric(10, 2), default=0.0) # Juros/Taxas
    data_pagamento = db.Column(db.DateTime, default=datetime.utcnow)
    transacao_financeira_id = db.Column(db.Integer, db.ForeignKey('transacoes_financeiras.id'), nullable=True)
    
    banco = db.relationship('Ativo', backref='pagamentos_fatura')
