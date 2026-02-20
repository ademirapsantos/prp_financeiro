import os
import subprocess
from flask import Flask, request, jsonify

app = Flask(__name__)
UPDATE_TOKEN = os.getenv('UPDATE_TOKEN', 'change_me_token')

@app.route('/health')
def health():
    return {"status": "updater-ready"}

@app.route('/api/update', methods=['POST'])
def update():
    token = request.headers.get('Authorization')
    if token != f"Bearer {UPDATE_TOKEN}":
        return jsonify({"error": "Unauthorized"}), 401
    
    try:
        # 1. Colocar em Manutenção (via shell command no app se necessário, 
        # mas aqui vamos apenas rodar os comandos docker)
        
        # 2. Pull da nova imagem
        subprocess.run(["docker-compose", "pull"], check=True)
        
        # 3. Rodar Migrações
        # Usamos o container da aplicação para rodar o alembic upgrade head
        # Mudança: Garantir que o container está up ou usar run --rm
        subprocess.run([
            "docker-compose", "run", "--rm", "prp-financeiro-test", 
            "alembic", "upgrade", "head"
        ], check=True)
        
        # 4. Restart containers
        subprocess.run(["docker-compose", "up", "-d"], check=True)
        
        return jsonify({"status": "success", "message": "Update completed and migrations applied."})
    except subprocess.CalledProcessError as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5005)
