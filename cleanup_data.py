import sys
from app import create_app, db
from app.models import Ativo, Titulo, LivroDiario, PartidaDiario, TransacaoFinanceira

def run_cleanup(dry_run=True):
    app = create_app()
    with app.app_context():
        print("--- Iniciando Auditoria de Limpeza ---")
        
        # 1. Ativos do tipo Veiculo
        ativos_veiculo = Ativo.query.filter_by(tipo='Veiculo').all()
        print(f"Ativos (Veiculo) para remover: {len(ativos_veiculo)}")
        
        # 2. Todos os Titulos (Compra/Venda)
        titulos = Titulo.query.all()
        print(f"Títulos para remover: {len(titulos)}")
        
        # 3. Lançamentos Contábeis (Balancete)
        partidas = PartidaDiario.query.all()
        diarios = LivroDiario.query.all()
        print(f"Lançamentos Diário para remover: {len(diarios)}")
        print(f"Partidas Diário para remover: {len(partidas)}")
        
        # 4. Transações Financeiras
        transacoes = TransacaoFinanceira.query.all()
        print(f"Transações Financeiras para remover: {len(transacoes)}")
        
        if dry_run:
            print("\nMODO DRY-RUN: Nenhuma alteração foi feita no banco de dados.")
            return

        print("\nEXCUTANDO LIMPEZA EFETIVA...")
        
        # Ordem importa por causa de FKs
        for p in partidas: db.session.delete(p)
        for d in diarios: db.session.delete(d)
        for t in transacoes: db.session.delete(t)
        for ti in titulos: db.session.delete(ti)
        for a in ativos_veiculo: db.session.delete(a)
        
        db.session.commit()
        print("LIMPEZA CONCLUÍDA COM SUCESSO!")

if __name__ == "__main__":
    is_dry = "--commit" not in sys.argv
    run_cleanup(dry_run=is_dry)
    if is_dry:
        print("\nUse 'python cleanup_data.py --commit' para realizar a limpeza.")
