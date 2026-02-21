import os

def env_bool(name, default=False):
    """
    Lê uma variável de ambiente e retorna um booleano.
    - True se: 1, true, yes, y, on
    - False se: 0, false, no, n, off, '' ou None
    - Caso valor desconhecido -> default
    """
    value = os.getenv(name)
    if value is None or value.strip() == '':
        return default
    
    normalized = value.strip().lower()
    if normalized in ('1', 'true', 'yes', 'y', 'on'):
        return True
    if normalized in ('0', 'false', 'no', 'n', 'off'):
        return False
    
    return default
