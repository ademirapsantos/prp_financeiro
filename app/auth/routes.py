from flask import render_template, redirect, url_for, flash, request, session, current_app, send_file
import os
import subprocess
import tempfile
from flask_login import login_user, logout_user, login_required, current_user
from . import auth_bp
from ..models import User, db, Configuracao, ContaContabil, LivroDiario, PartidaDiario, Entidade, Ativo, Titulo, TransacaoFinanceira, ConfiguracaoSMTP
import io
from datetime import datetime
from decimal import Decimal
import secrets
import string

def refresh_mail_config():
    """Atualiza as configurações do Flask-Mail e da instância global mail."""
    from .. import mail
    from ..models import ConfiguracaoSMTP
    
    cfg = ConfiguracaoSMTP.query.first()
    if not cfg:
        return
        
    server = cfg.smtp_server.strip()
    port = int(cfg.smtp_port)
    use_tls = cfg.use_tls
    use_ssl = cfg.use_ssl
    user = cfg.smtp_user.strip() if cfg.smtp_user else ''
    password = cfg.smtp_password.strip() if cfg.smtp_password else ''
    
    # Atualiza app.config
    current_app.config['MAIL_SERVER'] = server
    current_app.config['MAIL_PORT'] = port
    current_app.config['MAIL_USE_TLS'] = use_tls
    current_app.config['MAIL_USE_SSL'] = use_ssl
    current_app.config['MAIL_USERNAME'] = user
    current_app.config['MAIL_PASSWORD'] = password
    
    # CRITICAL: Atualiza a instância do Mail, pois ela não lê o config dinamicamente após init_app
    mail.server = server
    mail.port = port
    mail.use_tls = use_tls
    mail.use_ssl = use_ssl
    mail.username = user
    mail.password = password

def generate_temp_password(length=12):
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def send_email_direct(subject, recipient_email, body):
    """Envia um e-mail diretamente via smtplib usando as configurações do banco."""
    import smtplib
    import ssl
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    
    from ..models import ConfiguracaoSMTP
    
    cfg = ConfiguracaoSMTP.query.first()
    if not cfg:
        raise Exception("Servidor SMTP não configurado.")
    
    host = cfg.smtp_server
    port = int(cfg.smtp_port)
    user_smtp = cfg.smtp_user
    pass_smtp = cfg.smtp_password
    use_tls = cfg.use_tls
    use_ssl = cfg.use_ssl
    
    if not host or not user_smtp or not pass_smtp:
        raise Exception("Dados de SMTP (host/usuário/senha) incompletos no banco de dados.")
    
    # Criar a mensagem
    message = MIMEMultipart()
    message["From"] = user_smtp
    message["To"] = recipient_email
    message["Subject"] = subject
    message.attach(MIMEText(body, "plain"))
    
    if use_ssl and port == 465:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(host, port, context=context, timeout=15) as server:
            server.login(user_smtp, pass_smtp)
            server.send_message(message)
    else:
        with smtplib.SMTP(host, port, timeout=15) as server:
            if use_tls:
                server.starttls()
            server.login(user_smtp, pass_smtp)
            server.send_message(message)
    return True

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    # ... (unchanged logic)
    if User.query.count() > 0:
        flash('O sistema já possui um administrador cadastrado.', 'error')
        return redirect(url_for('auth.login'))
    
    if request.method == 'POST':
        nome = request.form.get('nome')
        email = request.form.get('email')
        
        if User.query.filter_by(email=email).first():
            flash('E-mail já cadastrado.', 'error')
            return redirect(url_for('auth.register'))
        
        temp_password = generate_temp_password()
        user = User(nome=nome, email=email, is_admin=True, deve_alterar_senha=True)
        user.set_password(temp_password)
        
        db.session.add(user)
        db.session.commit()
        
        return render_template('auth/temp_password.html', password=temp_password, email=email)
        
    return render_template('auth/register.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        if session.get('is_locked'):
            return redirect(url_for('auth.lock_screen'))
        return redirect(url_for('main.dashboard'))
        
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        
        if user and user.check_password(password):
            login_user(user)
            session['is_locked'] = False # Garantir que começa desbloqueado
            next_page = request.args.get('next')
            return redirect(next_page or url_for('main.dashboard'))
        else:
            flash('E-mail ou senha inválidos.', 'error')
            
    return render_template('auth/login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    session.pop('is_locked', None)
    logout_user()
    return redirect(url_for('auth.login'))

@auth_bp.route('/lock')
@login_required
def lock():
    session['is_locked'] = True
    return redirect(url_for('auth.lock_screen'))

@auth_bp.route('/unlock', methods=['GET', 'POST'])
@login_required
def lock_screen():
    if not session.get('is_locked'):
        return redirect(url_for('main.dashboard'))
        
    if request.method == 'POST':
        password = request.form.get('password')
        if current_user.check_password(password):
            session['is_locked'] = False
            flash('Sistema desbloqueado.', 'success')
            return redirect(url_for('main.dashboard'))
        else:
            flash('Senha incorreta.', 'error')
            
    return render_template('auth/lock_screen.html', user=current_user)

@auth_bp.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    # ... (manter original)
    if request.method == 'POST':
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        if not current_user.check_password(current_password):
            flash('Senha atual incorreta.', 'error')
        elif new_password != confirm_password:
            flash('As senhas não coincidem.', 'error')
        elif len(new_password) < 6:
            flash('A senha deve ter pelo menos 6 caracteres.', 'error')
        elif not any(c.isalpha() for c in new_password) or not any(c.isdigit() for c in new_password):
            flash('A senha deve conter letras e números.', 'error')
        else:
            current_user.set_password(new_password)
            current_user.deve_alterar_senha = False
            db.session.commit()
            flash('Senha alterada com sucesso!', 'success')
            return redirect(url_for('main.dashboard'))
            
    return render_template('auth/change_password.html')

# --- CONFIGURAÇÕES SMTP & RECUPERAÇÃO DE SENHA ---

@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')
        user = User.query.filter_by(email=email).first()
        
        if user:
            temp_password = generate_temp_password()
            user.set_password(temp_password)
            user.deve_alterar_senha = True
            db.session.commit()
            
            # Enviar e-mail
            try:
                body = f"Olá {user.nome},\n\nSua senha temporária é: {temp_password}\n\nPor favor, altere-a após o login."
                send_email_direct("Recuperação de Senha - PRP Financeiro", email, body)
                flash('E-mail enviado com sucesso! Verifique sua caixa de entrada.', 'success')
            except Exception as e:
                from ..models import ConfiguracaoSMTP
                cfg = ConfiguracaoSMTP.query.first()
                host = cfg.smtp_server if cfg else "None"
                port = cfg.smtp_port if cfg else "None"
                debug_info = f" (Host: {host}:{port})"
                flash(f'Erro ao enviar e-mail: {str(e)}{debug_info}. Senha gerada (para teste): {temp_password}', 'warning')
            
            return redirect(url_for('auth.login'))
        else:
            flash('E-mail não encontrado.', 'error')
            
    return render_template('auth/forgot_password.html')

@auth_bp.route('/api/config', methods=['GET', 'POST'])
@login_required
def manage_config():
    if not current_user.is_admin:
        return {"success": False, "message": "Acesso negado."}, 403
    from ..models import ConfiguracaoSMTP
    
    cfg = ConfiguracaoSMTP.query.first()
    if not cfg:
        cfg = ConfiguracaoSMTP()
        db.session.add(cfg)
        db.session.commit()
    
    if request.method == 'POST':
        data = request.get_json()
        try:
            if 'SMTP_HOST' in data: cfg.smtp_server = data['SMTP_HOST']
            if 'SMTP_PORT' in data: cfg.smtp_port = int(data['SMTP_PORT'])
            if 'SMTP_USER' in data: cfg.smtp_user = data['SMTP_USER']
            if 'SMTP_PASS' in data: cfg.smtp_password = data['SMTP_PASS']
            if 'SMTP_USE_TLS' in data: cfg.use_tls = str(data['SMTP_USE_TLS']).upper() == 'TRUE'
            if 'SMTP_USE_SSL' in data: cfg.use_ssl = str(data['SMTP_USE_SSL']).upper() == 'TRUE'
            
            db.session.commit()
            refresh_mail_config() # Atualiza em tempo real
            return {"success": True, "message": "Configurações SMTP salvas com sucesso!"}
        except Exception as e:
            db.session.rollback()
            return {"success": False, "message": str(e)}, 400
            
    # GET
    return {
        "SMTP_HOST": cfg.smtp_server,
        "SMTP_PORT": cfg.smtp_port,
        "SMTP_USER": cfg.smtp_user,
        "SMTP_PASS": cfg.smtp_password,
        "SMTP_USE_TLS": cfg.use_tls,
        "SMTP_USE_SSL": cfg.use_ssl
    }

@auth_bp.route('/api/users', methods=['GET'])
@login_required
def list_users():
    if not current_user.is_admin:
        return {"success": False, "message": "Acesso negado."}, 403
    users = User.query.all()
    user_list = []
    for user in users:
        user_list.append({
            "id": user.id,
            "nome": user.nome,
            "email": user.email,
            "is_admin": user.is_admin,
            "data_criacao": user.data_criacao.strftime('%d/%m/%Y %H:%M'),
            "deve_alterar_senha": user.deve_alterar_senha
        })
    return {"users": user_list}

@auth_bp.route('/api/users/add', methods=['POST'])
@login_required
def add_user():
    if not current_user.is_admin:
        return {"success": False, "message": "Acesso negado. Apenas administradores podem criar usuários."}, 403
    
    data = request.get_json()
    nome = data.get('nome')
    email = data.get('email')
    is_admin = data.get('is_admin', False)
    
    if not nome or not email:
        return {"success": False, "message": "Nome e E-mail são obrigatórios."}, 400
    
    if User.query.filter_by(email=email).first():
        return {"success": False, "message": "E-mail já cadastrado."}, 400
    
    # Gerar senha temporária
    temp_pass = generate_temp_password(length=8)
    
    user = User(nome=nome, email=email, is_admin=is_admin, deve_alterar_senha=True)
    user.set_password(temp_pass)
    
    db.session.add(user)
    db.session.commit()
    
    envio_email = False
    try:
        body = f"Olá {nome},\n\nSua conta no PRP Financeiro foi criada.\n\nSua senha temporária é: {temp_pass}\n\nPor favor, altere-a no seu primeiro acesso."
        send_email_direct("Bem-vindo ao PRP Financeiro", email, body)
        envio_email = True
    except Exception as e:
        print(f"Erro ao enviar e-mail de boas-vindas: {e}")

    message = f"Usuário {nome} cadastrado com sucesso!"
    if envio_email:
        message += " A senha temporária foi enviada para o e-mail do usuário."
    else:
        message += " ATENÇÃO: O e-mail não pôde ser enviado. Verifique as configurações de SMTP."

    return {
        "success": True, 
        "message": message
    }

@auth_bp.route('/api/users/<int:user_id>/delete', methods=['POST', 'DELETE'])
@login_required
def delete_user(user_id):
    if not current_user.is_admin:
        return {"success": False, "message": "Acesso negado. Apenas administradores podem excluir usuários."}, 403
    
    if current_user.id == user_id:
        return {"success": False, "message": "Você não pode excluir sua própria conta."}, 400
        
    user = User.query.get_or_404(user_id)
    
    try:
        db.session.delete(user)
        db.session.commit()
        return {"success": True, "message": f"Usuário {user.nome} excluído com sucesso!"}
    except Exception as e:
        db.session.rollback()
        return {"success": False, "message": f"Erro ao excluir usuário: {str(e)}"}, 400

@auth_bp.route('/api/users/<int:user_id>/resend-password', methods=['POST'])
@login_required
def resend_user_password(user_id):
    if not current_user.is_admin:
        return {"success": False, "message": "Acesso negado. Apenas administradores podem reenviar senhas."}, 403
    
    user = User.query.get_or_404(user_id)
    
    # Gerar nova senha temporária
    temp_pass = generate_temp_password(length=8)
    user.set_password(temp_pass)
    user.deve_alterar_senha = True
    
    try:
        db.session.commit()
        
        # Enviar e-mail diretamente
        try:
            body = f"Olá {user.nome},\n\nUma nova senha temporária foi gerada conforme solicitado.\n\nSua senha temporária é: {temp_pass}\n\nPor favor, altere-a no seu próximo acesso."
            send_email_direct("Sua nova senha - PRP Financeiro", user.email, body)
            return {"success": True, "message": f"Nova senha enviada para {user.email}"}
        except Exception as e:
            from ..models import ConfiguracaoSMTP
            cfg = ConfiguracaoSMTP.query.first()
            host = cfg.smtp_server if cfg else "None"
            port = cfg.smtp_port if cfg else "None"
            debug_info = f" (Host: {host}:{port})"
            return {"success": False, "message": f"Erro ao enviar e-mail: {str(e)}{debug_info}. Senha gerada (para cópia manual): {temp_pass}"}, 400
            
    except Exception as e:
        db.session.rollback()
        return {"success": False, "message": f"Erro ao atualizar senha no banco: {str(e)}"}, 400

@auth_bp.route('/api/backup/export', methods=['GET'])
@login_required
def export_backup():
    if not current_user.is_admin:
        return {"success": False, "message": "Acesso negado."}, 403

    from ..config import Config
    db_url = Config.get_sqlalchemy_uri()

    temp_file = tempfile.NamedTemporaryFile(suffix='.dump', delete=False)
    temp_file.close()
    dump_path = temp_file.name

    try:
        cmd = [
            'pg_dump',
            '--dbname', db_url,
            '--format=custom',
            '--no-owner',
            '--no-privileges',
            '--file', dump_path,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise Exception(result.stderr or result.stdout or 'Falha no pg_dump')

        with open(dump_path, 'rb') as f:
            memory_file = io.BytesIO(f.read())
        memory_file.seek(0)

        filename = f"backup_prp_{datetime.now().strftime('%Y%m%d_%H%M%S')}.dump"
        return send_file(
            memory_file,
            mimetype='application/octet-stream',
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        return {"success": False, "message": f"Erro ao exportar backup Postgres: {str(e)}"}, 500
    finally:
        if os.path.exists(dump_path):
            os.remove(dump_path)
@auth_bp.route('/api/backup/restore', methods=['POST'])
@login_required
def restore_backup():
    if not current_user.is_admin:
        return {"success": False, "message": "Acesso negado."}, 403

    from ..config import Config

    file = request.files.get('file')
    if not file:
        return {"success": False, "message": "Nenhum arquivo enviado."}, 400

    Configuracao.set_valor('MAINTENANCE_MODE', 'true', 'Sistema em restauracao de backup')

    temp_file = tempfile.NamedTemporaryFile(suffix='.dump', delete=False)
    temp_file.close()

    try:
        if not file.filename or not (file.filename.endswith('.dump') or file.filename.endswith('.backup')):
            raise Exception('Formato nao suportado. Envie um backup Postgres (.dump ou .backup).')

        file.save(temp_file.name)
        db_url = Config.get_sqlalchemy_uri()

        db.session.remove()
        db.engine.dispose()

        cmd = [
            'pg_restore',
            '--dbname', db_url,
            '--clean',
            '--if-exists',
            '--no-owner',
            '--no-privileges',
            temp_file.name,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise Exception(result.stderr or result.stdout or 'Falha no pg_restore')

        Configuracao.set_valor('MAINTENANCE_MODE', 'false')
        return {"success": True, "message": "Backup Postgres restaurado com sucesso."}

    except Exception as e:
        db.session.rollback()
        Configuracao.set_valor('MAINTENANCE_MODE', 'false')
        return {"success": False, "message": f"Erro no restore: {str(e)}"}, 500
    finally:
        if os.path.exists(temp_file.name):
            os.remove(temp_file.name)
@auth_bp.route('/api/perfil/tema', methods=['POST'])
@login_required
def update_theme():
    data = request.get_json()
    tema = data.get('tema')
    
    if tema not in ['light', 'dark']:
        return {"success": False, "message": "Tema inválido."}, 400
        
    current_user.tema = tema
    db.session.commit()
    return {"success": True, "tema": tema}


