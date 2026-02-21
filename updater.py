import os
import subprocess
import time
import json
import uuid
import requests
from datetime import datetime
from flask import Flask, request, jsonify

app = Flask(__name__)

# Configurações via Variáveis de Ambiente
UPDATE_TOKEN = os.getenv('UPDATE_TOKEN', 'change_me_token')
COMPOSE_FILE = os.getenv('COMPOSE_FILE', 'docker-compose.yml')
SERVICE_NAME = os.getenv('SERVICE_NAME', 'prp-financeiro')
PROJECT_DIR = os.getenv('PROJECT_DIR', '/app')
ENVIRONMENT = os.getenv('ENVIRONMENT', 'dev')
MANIFEST_BASE_URL = os.getenv('MANIFEST_BASE_URL', 'https://ademirapsantos.github.io/prp_financeiro')
GHCR_IMAGE = os.getenv('GHCR_IMAGE', 'ghcr.io/ademirapsantos/prp_financeiro')
PROJECT_NAME = os.getenv('COMPOSE_PROJECT_NAME', 'prp_financeiro')
APP_HOST = os.getenv('APP_HOST', 'prp-financeiro-hml' if ENVIRONMENT == 'hml' else 'prp-financeiro-prod' if ENVIRONMENT == 'prod' else 'prp-financeiro')
APP_PORT = os.getenv('APP_PORT', '5000')
KEEP_IMAGES = int(os.getenv('KEEP_IMAGES', '3'))
APP_FINALIZE_URL = os.getenv('APP_FINALIZE_URL', f'http://{APP_HOST}:{APP_PORT}/api/system/update/finalize-token')
UPDATER_HEALTH_ATTEMPTS = int(os.getenv('UPDATER_HEALTH_ATTEMPTS', '15'))
UPDATER_HEALTH_SLEEP_SECONDS = int(os.getenv('UPDATER_HEALTH_SLEEP_SECONDS', '10'))

# Caminhos de Arquivos
DATA_DIR = os.path.join(PROJECT_DIR, 'data')
LOCK_FILE = os.path.join(DATA_DIR, 'update.lock')
LOG_FILE = os.path.join(DATA_DIR, 'update_logs.jsonl')
STATE_FILE = os.path.join(DATA_DIR, 'update_state.json')
ENV_FILE = os.path.join(PROJECT_DIR, f'.env.{ENVIRONMENT}' if os.path.exists(os.path.join(PROJECT_DIR, f'.env.{ENVIRONMENT}')) else '.env')

os.makedirs(DATA_DIR, exist_ok=True)

def log_event(event_type, details=None):
    """Registra um evento no log JSONL."""
    log_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "event": event_type,
        "details": details or {}
    }
    try:
        with open(LOG_FILE, 'a') as f:
            f.write(json.dumps(log_entry) + '\n')
    except:
        pass

def create_backup():
    """Cria um backup do banco de dados SQLite."""
    backup_dir = os.path.join(DATA_DIR, 'backups')
    os.makedirs(backup_dir, exist_ok=True)
    
    # Tenta descobrir o caminho do banco através do ambiente ou padrão
    db_path = os.path.join(DATA_DIR, 'prp_financeiro.db')
    
    if os.path.exists(db_path):
        timestamp = datetime.now().strftime('%Y%mm%dd_%HH%MM%SS')
        backup_file = os.path.join(backup_dir, f'prp_financeiro_{timestamp}.db')
        
        try:
            import shutil
            shutil.copy2(db_path, backup_file)
            log_event("backup_created", {"path": backup_file})
            return backup_file
        except Exception as e:
            log_event("backup_failed", {"error": str(e)})
            # Não interrompe o update se o backup falhar, mas loga
    return None

def save_state(state):
    """Salva o estado atual para rollback."""
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f)

def load_state():
    """Carrega o estado salvo."""
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r') as f:
            return json.load(f)
    return {}

def get_current_tag():
    """Lê a tag atual do arquivo .env."""
    env_key = f'PRP_IMAGE_{ENVIRONMENT.upper()}'
    if not os.path.exists(ENV_FILE):
        return None
    with open(ENV_FILE, 'r') as f:
        for line in f:
            if line.startswith(f'{env_key}='):
                val = line.strip().split('=')[1]
                return val.split(':')[-1] if ':' in val else 'latest'
    return None

def set_env_tag(tag):
    """Atualiza a tag no arquivo .env."""
    env_key = f'PRP_IMAGE_{ENVIRONMENT.upper()}'
    new_value = f'{GHCR_IMAGE}:{tag}'
    lines = []
    found = False
    
    if os.path.exists(ENV_FILE):
        with open(ENV_FILE, 'r') as f:
            for line in f:
                if line.startswith(f'{env_key}='):
                    lines.append(f'{env_key}={new_value}\n')
                    found = True
                else:
                    lines.append(line)
    
    if not found:
        lines.append(f'{env_key}={new_value}\n')
        
    with open(ENV_FILE, 'w') as f:
        f.writelines(lines)

def run_docker_command(cmd_args):
    """Executa comando docker compose com nome do projeto fixo."""
    full_cmd = ["docker", "compose", "-p", PROJECT_NAME, "-f", COMPOSE_FILE] + cmd_args
    result = subprocess.run(full_cmd, cwd=PROJECT_DIR, capture_output=True, text=True)
    if result.returncode != 0:
        error_msg = result.stderr or result.stdout
        raise Exception(f"Docker command failed: {error_msg}")
    return result.stdout

def check_container_health():
    """Verifica se o app está respondendo /health via HTTP dentro da rede do docker."""
    health_url = f"http://{APP_HOST}:{APP_PORT}/health"
    log_event("health_check_start", {"url": health_url})
    
    for i in range(UPDATER_HEALTH_ATTEMPTS):
        try:
            time.sleep(UPDATER_HEALTH_SLEEP_SECONDS)
            res = requests.get(health_url, timeout=5)
            if res.status_code == 200 or res.status_code == 503:
                data = res.json()
                # 503 com status maintenance é considerado "vivo" para o updater
                if data.get('status') in ['healthy', 'maintenance']:
                    log_event("health_check_success", {"attempt": i+1, "status": data.get('status')})
                    return True
        except Exception as e:
            log_event("health_check_attempt_failed", {"attempt": i+1, "error": str(e)})
            
    return False

def finalize_update_state(status, error_message=''):
    """Notifica o app principal para finalizar flags de manutenção/update."""
    payload = {"status": status}
    if error_message:
        payload["error"] = error_message

    headers = {"Authorization": f"Bearer {UPDATE_TOKEN}"}

    for attempt in range(1, 16):
        try:
            res = requests.post(APP_FINALIZE_URL, json=payload, headers=headers, timeout=5)
            if res.status_code == 200:
                log_event("finalize_notified", {"status": status, "attempt": attempt})
                return True
            log_event("finalize_failed_status", {"attempt": attempt, "status_code": res.status_code, "body": res.text})
        except Exception as e:
            log_event("finalize_failed_exception", {"attempt": attempt, "error": str(e)})
        time.sleep(2)

    return False

def cleanup_images():
    """Remove imagens antigas do ambiente, mantendo apenas as N mais recentes."""
    try:
        log_event("cleanup_started")
        # Listar imagens do repositório ghcr filtrando pelo ambiente
        cmd = ["docker", "images", "--format", "{{.Repository}}:{{.Tag}}|{{.CreatedAt}}", GHCR_IMAGE]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            return
            
        lines = result.stdout.strip().split('\n')
        # Formato: ghcr.io/repo:tag|2026-02-20 ...
        images = []
        for line in lines:
            if '|' in line:
                name_tag, created = line.split('|')
                images.append({"name": name_tag, "created": created})
        
        # Ordenar por data (mais recente primeiro)
        images.sort(key=lambda x: x['created'], reverse=True)
        
        if len(images) > KEEP_IMAGES:
            to_remove = images[KEEP_IMAGES:]
            for img in to_remove:
                # Tenta remover, ignora erro se estiver em uso
                subprocess.run(["docker", "rmi", img['name']], capture_output=True)
                log_event("image_removed", {"tag": img['name']})
                
        log_event("cleanup_finished")
    except Exception as e:
        log_event("cleanup_failed", {"error": str(e)})

@app.route('/health')
def health():
    return {"status": "ok", "service": "updater"}

@app.route('/api/update', methods=['POST'])
def perform_update():
    token = request.headers.get('Authorization')
    if token != f"Bearer {UPDATE_TOKEN}":
        return jsonify({"error": "Unauthorized"}), 401
    
    if os.path.exists(LOCK_FILE):
        return jsonify({"error": "Update already in progress"}), 409
    
    update_id = str(uuid.uuid4())
    previous_tag = None
    target_tag = None
    env_tag_switched = False
    try:
        # 1. Lock
        with open(LOCK_FILE, 'w') as f:
            f.write(update_id)
        
        log_event("update_start", {"update_id": update_id, "env": ENVIRONMENT})
        
        # 2. Fetch Manifest
        manifest_url = f"{MANIFEST_BASE_URL}/{ENVIRONMENT}.json"
        res = requests.get(manifest_url, timeout=10)
        res.raise_for_status()
        manifest = res.json()
        target_tag = manifest.get('tag')
        
        if not target_tag:
            raise Exception("Manifest does not contain a 'tag' key")
            
        previous_tag = get_current_tag()
        log_event("target_version", {"tag": target_tag, "previous_tag": previous_tag})
        
        # 2.5 Backup preventivo
        create_backup()
        
        # Salva estado antes de alterar
        save_state({"previous_tag": previous_tag, "target_tag": target_tag, "timestamp": datetime.now().isoformat()})
        
        # 3. Pull and Deploy
        set_env_tag(target_tag)
        env_tag_switched = True
        run_docker_command(["rm", "-sf", SERVICE_NAME])
        run_docker_command(["pull", SERVICE_NAME])
        run_docker_command(["up", "-d", "--no-deps", "--force-recreate", SERVICE_NAME])
        log_event("deploy_started")
        
        # 4. Health Check
        is_healthy = check_container_health()
        
        if is_healthy:
            log_event("update_success", {"new_tag": target_tag})
            # Limpeza de imagens pós-sucesso
            cleanup_images()
            finalize_update_state("success")
            os.remove(LOCK_FILE)
            return jsonify({"status": "success", "update_id": update_id})
        else:
            # 5. Rollback
            log_event("health_failed", {"action": "auto_rollback"})
            if previous_tag:
                set_env_tag(previous_tag)
                run_docker_command(["up", "-d", "--no-deps", "--force-recreate", SERVICE_NAME])
                log_event("rollback_completed", {"restored_tag": previous_tag})
                finalize_update_state("failed", "App unhealthy after update. Rollback performed.")
                os.remove(LOCK_FILE)
                return jsonify({"error": "health_failed", "details": "App unhealthy after update. Rollback performed."}), 500
            else:
                finalize_update_state("failed", "App unhealthy and no previous tag for rollback.")
                os.remove(LOCK_FILE)
                return jsonify({"error": "health_failed", "details": "App unhealthy and no previous tag for rollback."}), 500
                
    except Exception as e:
        error_message = str(e)
        log_event("update_error", {"error": error_message})

        if env_tag_switched and previous_tag:
            try:
                set_env_tag(previous_tag)
                run_docker_command(["up", "-d", "--no-deps", "--force-recreate", SERVICE_NAME])
                log_event("rollback_after_exception", {"restored_tag": previous_tag, "failed_target_tag": target_tag})
            except Exception as rb_error:
                log_event("rollback_after_exception_failed", {"error": str(rb_error)})

        finalize_update_state("failed", error_message)

        if os.path.exists(LOCK_FILE):
            os.remove(LOCK_FILE)
        return jsonify({"error": "docker_compose_failed", "details": error_message}), 500

@app.route('/api/rollback', methods=['POST'])
def manual_rollback():
    token = request.headers.get('Authorization')
    if token != f"Bearer {UPDATE_TOKEN}":
        return jsonify({"error": "Unauthorized"}), 401
    
    # Implementação manual se necessário, mas o auto já cobre o caso crítico
    return jsonify({"message": "Manual rollback logic is built into auto-rollback storage"}), 501

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5005)
