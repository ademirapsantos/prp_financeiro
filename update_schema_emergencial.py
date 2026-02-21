import os
import sys
from sqlalchemy import text

# Adiciona o diretório atual ao path para resolver as importações
sys.path.append(os.getcwd())

from app import create_app, db

def atualizar_esquema_emergencial():
    app = create_app()
    with app.app_context():
        print("Iniciando atualização de esquema para limite emergencial e encargos...")
        
        queries = [
            "ALTER TABLE cartoes_credito ADD COLUMN perc_limite_emergencial NUMERIC(5, 2) DEFAULT 0.0",
            "ALTER TABLE cartoes_credito ADD COLUMN limite_emergencial_ativo BOOLEAN DEFAULT 0",
            "ALTER TABLE pagamentos_fatura_cartao ADD COLUMN valor_encargos NUMERIC(10, 2) DEFAULT 0.0"
        ]
        
        for q in queries:
            try:
                db.session.execute(text(q))
                db.session.commit()
                print(f"Sucesso: {q}")
            except Exception as e:
                print(f"Ignorado (já existe ou erro): {q[:40]}... -> {str(e)[:50]}")
        
        # Ajustar valores nulos para o padrão se necessário
        try:
            db.session.execute(text("UPDATE cartoes_credito SET perc_limite_emergencial = 0.0 WHERE perc_limite_emergencial IS NULL"))
            db.session.execute(text("UPDATE cartoes_credito SET limite_emergencial_ativo = 0 WHERE limite_emergencial_ativo IS NULL"))
            db.session.execute(text("UPDATE pagamentos_fatura_cartao SET valor_encargos = 0.0 WHERE valor_encargos IS NULL"))
            db.session.commit()
            print("Valores padrão aplicados.")
        except Exception as e:
            print(f"Erro ao aplicar padrões: {e}")

        print("Esquema atualizado!")

if __name__ == "__main__":
    atualizar_esquema_emergencial()
