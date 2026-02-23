import os


class Config:
    ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    BACKUP_DIR = os.path.join(ROOT_DIR, 'backup')

    for directory in [BACKUP_DIR]:
        if not os.path.exists(directory):
            os.makedirs(directory)

    @staticmethod
    def _env_file_candidates():
        env_name = (os.getenv('ENVIRONMENT', 'dev') or 'dev').strip().lower()
        return [
            os.path.join(Config.ROOT_DIR, f'.env.{env_name}'),
            os.path.join(Config.ROOT_DIR, '.env'),
        ]

    @staticmethod
    def _read_env_file_value(key):
        for env_file in Config._env_file_candidates():
            if not os.path.exists(env_file):
                continue

            try:
                with open(env_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith('#') or '=' not in line:
                            continue
                        k, v = line.split('=', 1)
                        if k.strip() == key:
                            return v.strip()
            except Exception:
                continue
        return None

    @staticmethod
    def get_sqlalchemy_uri():
        env_name = os.getenv('ENVIRONMENT', 'dev').upper()
        db_uri = os.getenv('DATABASE_URL')

        if not db_uri:
            db_uri = os.getenv(f'DATABASE_URL_{env_name}')

        if not db_uri:
            db_uri = Config._read_env_file_value('DATABASE_URL')

        if not db_uri:
            db_uri = Config._read_env_file_value(f'DATABASE_URL_{env_name}')

        if not db_uri:
            raise RuntimeError(
                'DATABASE_URL nao configurada. Defina DATABASE_URL ou DATABASE_URL_<AMBIENTE> no .env/ambiente.'
            )

        if db_uri.startswith('postgres://'):
            db_uri = db_uri.replace('postgres://', 'postgresql+psycopg://', 1)
        elif db_uri.startswith('postgresql://') and '+psycopg' not in db_uri:
            db_uri = db_uri.replace('postgresql://', 'postgresql+psycopg://', 1)

        if not db_uri.startswith('postgresql+psycopg://'):
            raise RuntimeError('DATABASE_URL invalida para PostgreSQL.')

        return db_uri
