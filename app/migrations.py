import logging
from . import db
from sqlalchemy import text, inspect

logger = logging.getLogger(__name__)

def run_migrations():
    """
    Executa migrações defensivas no PostgreSQL.
    Adiciona colunas faltantes e garante que tabelas existam.
    NUNCA apaga dados ou colunas.
    """
    logger.info("Iniciando migrações defensivas...")
    
    try:
        # 1. Garantir que as tabelas básicas existam (db.create_all já faz isso, mas aqui reforçamos)
        # Se algum dia mudarmos para algo mais complexo que create_all, faríamos aqui.
        
        # 2. Exemplo de migração de coluna (adicionar colunas que venham em versões novas)
        # Caso queira adicionar uma coluna 'timezone' na tabela 'users':
        # _add_column_if_not_exists('users', 'timezone', 'VARCHAR(50) DEFAULT "UTC"')
        
        # Adicione aqui futuras migrações de esquema
        pass
        
        logger.info("Migrações concluídas com sucesso.")
    except Exception as e:
        logger.error(f"Erro durante as migrações: {e}")
        # Não interrompe o app, mas loga o erro crítico
        raise e

def _add_column_if_not_exists(table_name, column_name, column_type):
    """Auxiliar para adicionar coluna apenas se ela não existir."""
    inspector = inspect(db.engine)
    columns = [c['name'] for c in inspector.get_columns(table_name)]
    
    if column_name not in columns:
        logger.info(f"Adicionando coluna '{column_name}' à tabela '{table_name}'...")
        try:
            with db.engine.connect() as conn:
                conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"))
                conn.commit()
            logger.info(f"Coluna '{column_name}' adicionada com sucesso.")
        except Exception as e:
            logger.error(f"Falha ao adicionar coluna '{column_name}': {e}")
            raise e
    else:
        logger.debug(f"Coluna '{column_name}' já existe na tabela '{table_name}'.")
