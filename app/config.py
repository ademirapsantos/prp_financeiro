import os

class Config:
    ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    DATA_DIR = os.path.join(ROOT_DIR, 'data')
    BACKUP_DIR = os.path.join(ROOT_DIR, 'backup')
    
    # Criar pastas se não existirem
    for directory in [DATA_DIR, BACKUP_DIR]:
        if not os.path.exists(directory):
            os.makedirs(directory)
            
    DEFAULT_DB_PATH = os.path.join(DATA_DIR, 'prp_financeiro.db')
    
    @staticmethod
    def get_sqlalchemy_uri():
        db_uri = os.getenv('DATABASE_URL')
        if not db_uri:
            # Prioriza DATABASE_PATH vindo do ambiente (Docker)
            db_path = os.getenv('DATABASE_PATH', Config.DEFAULT_DB_PATH)
            # Garante que o diretório pai existe
            os.makedirs(os.path.dirname(db_path), exist_ok=True)
            db_uri = f'sqlite:///{db_path}'
        return db_uri

    @staticmethod
    def get_db_path():
        # Extrai o caminho do arquivo da URI do SQLite
        uri = Config.get_sqlalchemy_uri()
        if uri.startswith('sqlite:///'):
            return uri.replace('sqlite:///', '')
        return Config.DEFAULT_DB_PATH
