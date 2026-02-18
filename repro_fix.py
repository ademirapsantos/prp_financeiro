from app import create_app, db
from app.models import Entidade, Titulo, LivroDiario, PartidaDiario, Ativo, ContaContabil
from app.services import FinancialService
from decimal import Decimal
from datetime import datetime

app = create_app()
with app.app_context():
    print("--- Verificação de Impacto na Criação de Título ---")
    
    # Pegar uma entidade qualquer
    entidade = Entidade.query.first()
    if not entidade:
        print("Erro: Nenhuma entidade para teste.")
        exit()
        
    print(f"Entidade: {entidade.nome}")
    
    # Saldo inicial do diário e ativos
    diario_count_antes = LivroDiario.query.count()
    partida_count_antes = PartidaDiario.query.count()
    saldos_ativos_antes = {a.id: float(a.valor_atual) for a in Ativo.query.all()}
    
    print(f"Lançamentos antes: {diario_count_antes}")
    
    # Criar título
    titulo = FinancialService.criar_titulo_receber(
        entidade=entidade,
        descricao="Teste Depuracao Impacto",
        valor=Decimal("123.45"),
        data_vencimento=datetime.now()
    )
    db.session.commit()
    
    print(f"Título criado (ID: {titulo.id})")
    
    # Verificar depois
    diario_count_depois = LivroDiario.query.count()
    partida_count_depois = PartidaDiario.query.count()
    saldos_ativos_depois = {a.id: float(a.valor_atual) for a in Ativo.query.all()}
    
    print(f"Lançamentos depois: {diario_count_depois}")
    
    if diario_count_depois > diario_count_antes:
        print("ALERTA: Um novo lançamento foi criado no diário!")
        novo_diario = LivroDiario.query.order_by(LivroDiario.id.desc()).first()
        print(f"Histórico: {novo_diario.historico}")
    else:
        print("Sucesso: Nenhum lançamento criado no diário.")
        
    for aid, valor in saldos_ativos_depois.items():
        if valor != saldos_ativos_antes.get(aid):
            ativo = db.session.get(Ativo, aid)
            print(f"ALERTA: Saldo do Ativo '{ativo.descricao}' mudou de {saldos_ativos_antes[aid]} para {valor}")
            
    print("--- Fim da Verificação ---")
