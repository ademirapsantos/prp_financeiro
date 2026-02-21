import os

def env_bool(name: str, default: bool=False) -> bool:
    """
    Lê uma variável de ambiente e retorna um booleano de forma robusta.
    - True se: 1, true, yes, y, on
    - False se: 0, false, no, n, off ou string vazia
    - Caso contrário retorna o default.
    """
    val = os.getenv(name)
    if val is None:
        return default
    
    val = val.strip().lower()
    if val in ("1", "true", "yes", "y", "on"):
        return True
    if val in ("0", "false", "no", "n", "off", ""):
        return False
    
    return default
