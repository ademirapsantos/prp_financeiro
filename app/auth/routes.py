from flask import render_template, redirect, url_for, flash, request, session, current_app, send_file
import os
import subprocess
import tempfile
import shutil
from flask_login import login_user, logout_user, login_required, current_user
from . import auth_bp
from ..models import User, db, Configuracao, ContaContabil, LivroDiario, PartidaDiario, Entidade, Ativo, Titulo, TransacaoFinanceira, ConfiguracaoSMTP
import io
from datetime import datetime
from decimal import Decimal
import secrets
import string
from urllib.parse import urlparse, urlunparse
from sqlalchemy import text

def _read_runtime_env_value(key):
    value = os.getenv(key)
    if value:
        return value

    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    env_name = (os.getenv('ENVIRONMENT', 'dev') or 'dev').strip().lower()
    candidates = [
        os.path.join(root_dir, f'.env.{env_name}'),
        os.path.join(root_dir, '.env'),
    ]
    for env_file in candidates:
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

def _resolve_pg_bin(binary_name):
    """
    Resolve caminho do binario pg_dump/pg_restore.
    Prioridade:
    1) PG_BIN_DIR (diretorio base comum para ambos binarios)
    2) variavel de ambiente explicita (PG_DUMP_BIN / PG_RESTORE_BIN)
    3) PATH do sistema (shutil.which)
    4) caminhos comuns Linux e Windows
    """
    exe_name = f'{binary_name}.exe' if os.name == 'nt' else binary_name

    pg_bin_dir = _read_runtime_env_value('PG_BIN_DIR')
    if pg_bin_dir:
        candidate = os.path.join(pg_bin_dir, exe_name)
        if os.path.exists(candidate):
            return candidate

    env_key_map = {
        'pg_dump': 'PG_DUMP_BIN',
        'pg_restore': 'PG_RESTORE_BIN',
        'psql': 'PSQL_BIN',
    }
    env_key = env_key_map.get(binary_name)
    explicit = _read_runtime_env_value(env_key)
    if explicit:
        if os.path.exists(explicit):
            return explicit
        explicit_found = shutil.which(explicit)
        if explicit_found:
            return explicit_found

    found = shutil.which(binary_name)
    if found:
        return found

    linux_candidates = [
        f'/usr/local/bin/{binary_name}',
        f'/usr/bin/{binary_name}',
        f'/bin/{binary_name}',
    ]
    for candidate in linux_candidates:
        if os.path.exists(candidate):
            return candidate

    if os.name == 'nt':
        program_files = os.getenv('ProgramFiles', r'C:\Program Files')
        for version in ('18', '17', '16', '15', '14', '13', '12'):
            candidate = os.path.join(program_files, 'PostgreSQL', version, 'bin', f'{binary_name}.exe')
            if os.path.exists(candidate):
                return candidate

    raise FileNotFoundError(
        f'{binary_name} nao encontrado no servidor. '
        f'Configure PG_BIN_DIR ou {"PG_DUMP_BIN" if binary_name == "pg_dump" else "PG_RESTORE_BIN"}.'
    )

def _to_pg_tools_uri(db_url):
    """
    Converte URL do SQLAlchemy (postgresql+psycopg://) para formato aceito por
    pg_dump/pg_restore (postgresql://).
    """
    if not db_url:
        return db_url
    if db_url.startswith('postgresql+psycopg://'):
        return db_url.replace('postgresql+psycopg://', 'postgresql://', 1)
    return db_url

def _fallback_local_db_url(db_url, error_text):
    """
    Fallback para DEV local quando o host do DB Ã© nome de serviÃ§o Docker
    (ex.: prp-postgres-test), mas o processo Flask estÃ¡ fora da rede Docker.
    """
    if not db_url or not error_text:
        return None

    lowered = error_text.lower()
    if 'could not translate host name' not in lowered and 'name or service not known' not in lowered:
        return None

    parsed = urlparse(db_url)
    host = parsed.hostname or ''
    if not host.startswith('prp-postgres-'):
        return None

    if host.endswith('-test'):
        port = 5435
    elif host.endswith('-hml'):
        port = 5433
    else:
        port = parsed.port or 5432

    netloc = parsed.netloc
    if '@' in netloc:
        auth, _ = netloc.rsplit('@', 1)
        new_netloc = f"{auth}@127.0.0.1:{port}"
    else:
        new_netloc = f"127.0.0.1:{port}"

    return urlunparse((parsed.scheme, new_netloc, parsed.path, parsed.params, parsed.query, parsed.fragment))

def _truncate_public_tables_for_sql_restore():
    """
    Limpa dados de todas as tabelas do schema public antes de restore .sql
    (data-only), evitando conflito de chave única em base já populada.
    """
    protected_tables = {'alembic_version'}
    with db.engine.begin() as conn:
        rows = conn.execute(text("""
            SELECT tablename
            FROM pg_tables
            WHERE schemaname = 'public'
        """)).fetchall()

        table_names = [r[0] for r in rows if r[0] not in protected_tables]
        if not table_names:
            return

        quoted_tables = ', '.join([f'"{name.replace(chr(34), chr(34) * 2)}"' for name in table_names])
        conn.execute(text(f"TRUNCATE TABLE {quoted_tables} RESTART IDENTITY CASCADE"))

def refresh_mail_config():
    """Atualiza as configuraÃ§Ãµes do Flask-Mail e da instÃ¢ncia global mail."""
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
    
    # CRITICAL: Atualiza a instÃ¢ncia do Mail, pois ela nÃ£o lÃª o config dinamicamente apÃ³s init_app
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
    """Envia um e-mail diretamente via smtplib usando as configuraÃ§Ãµes do banco."""
    import smtplib
    import ssl
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    
    from ..models import ConfiguracaoSMTP
    
    cfg = ConfiguracaoSMTP.query.first()
    if not cfg:
        raise Exception("Servidor SMTP nÃ£o configurado.")
    
    host = cfg.smtp_server
    port = int(cfg.smtp_port)
    user_smtp = cfg.smtp_user
    pass_smtp = cfg.smtp_password
    use_tls = cfg.use_tls
    use_ssl = cfg.use_ssl
    
    if not host or not user_smtp or not pass_smtp:
        raise Exception("Dados de SMTP (host/usuÃ¡rio/senha) incompletos no banco de dados.")
    
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
        flash('O sistema jÃ¡ possui um administrador cadastrado.', 'error')
        return redirect(url_for('auth.login'))
    
    if request.method == 'POST':
        nome = request.form.get('nome')
        email = request.form.get('email')
        
        if User.query.filter_by(email=email).first():
            flash('E-mail jÃ¡ cadastrado.', 'error')
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
            session['is_locked'] = False # Garantir que comeÃ§a desbloqueado
            next_page = request.args.get('next')
            return redirect(next_page or url_for('main.dashboard'))
        else:
            flash('E-mail ou senha invÃ¡lidos.', 'error')
            
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
            flash('As senhas nÃ£o coincidem.', 'error')
        elif len(new_password) < 6:
            flash('A senha deve ter pelo menos 6 caracteres.', 'error')
        elif not any(c.isalpha() for c in new_password) or not any(c.isdigit() for c in new_password):
            flash('A senha deve conter letras e nÃºmeros.', 'error')
        else:
            current_user.set_password(new_password)
            current_user.deve_alterar_senha = False
            db.session.commit()
            flash('Senha alterada com sucesso!', 'success')
            return redirect(url_for('main.dashboard'))
            
    return render_template('auth/change_password.html')

# --- CONFIGURAÃ‡Ã•ES SMTP & RECUPERAÃ‡ÃƒO DE SENHA ---

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
                body = f"OlÃ¡ {user.nome},\n\nSua senha temporÃ¡ria Ã©: {temp_password}\n\nPor favor, altere-a apÃ³s o login."
                send_email_direct("RecuperaÃ§Ã£o de Senha - PRP Financeiro", email, body)
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
            flash('E-mail nÃ£o encontrado.', 'error')
            
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
            return {"success": True, "message": "ConfiguraÃ§Ãµes SMTP salvas com sucesso!"}
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
        return {"success": False, "message": "Acesso negado. Apenas administradores podem criar usuÃ¡rios."}, 403
    
    data = request.get_json()
    nome = data.get('nome')
    email = data.get('email')
    is_admin = data.get('is_admin', False)
    
    if not nome or not email:
        return {"success": False, "message": "Nome e E-mail sÃ£o obrigatÃ³rios."}, 400
    
    if User.query.filter_by(email=email).first():
        return {"success": False, "message": "E-mail jÃ¡ cadastrado."}, 400
    
    # Gerar senha temporÃ¡ria
    temp_pass = generate_temp_password(length=8)
    
    user = User(nome=nome, email=email, is_admin=is_admin, deve_alterar_senha=True)
    user.set_password(temp_pass)
    
    db.session.add(user)
    db.session.commit()
    
    envio_email = False
    try:
        body = f"OlÃ¡ {nome},\n\nSua conta no PRP Financeiro foi criada.\n\nSua senha temporÃ¡ria Ã©: {temp_pass}\n\nPor favor, altere-a no seu primeiro acesso."
        send_email_direct("Bem-vindo ao PRP Financeiro", email, body)
        envio_email = True
    except Exception as e:
        print(f"Erro ao enviar e-mail de boas-vindas: {e}")

    message = f"UsuÃ¡rio {nome} cadastrado com sucesso!"
    if envio_email:
        message += " A senha temporÃ¡ria foi enviada para o e-mail do usuÃ¡rio."
    else:
        message += " ATENÃ‡ÃƒO: O e-mail nÃ£o pÃ´de ser enviado. Verifique as configuraÃ§Ãµes de SMTP."

    return {
        "success": True, 
        "message": message
    }

@auth_bp.route('/api/users/<user_id>/delete', methods=['POST', 'DELETE'])
@login_required
def delete_user(user_id):
    if not current_user.is_admin:
        return {"success": False, "message": "Acesso negado. Apenas administradores podem excluir usuÃ¡rios."}, 403
    
    if current_user.id == user_id:
        return {"success": False, "message": "VocÃª nÃ£o pode excluir sua prÃ³pria conta."}, 400
        
    user = User.query.get_or_404(user_id)
    
    try:
        db.session.delete(user)
        db.session.commit()
        return {"success": True, "message": f"UsuÃ¡rio {user.nome} excluÃ­do com sucesso!"}
    except Exception as e:
        db.session.rollback()
        return {"success": False, "message": f"Erro ao excluir usuÃ¡rio: {str(e)}"}, 400

@auth_bp.route('/api/users/<user_id>/resend-password', methods=['POST'])
@login_required
def resend_user_password(user_id):
    if not current_user.is_admin:
        return {"success": False, "message": "Acesso negado. Apenas administradores podem reenviar senhas."}, 403
    
    user = User.query.get_or_404(user_id)
    
    # Gerar nova senha temporÃ¡ria
    temp_pass = generate_temp_password(length=8)
    user.set_password(temp_pass)
    user.deve_alterar_senha = True
    
    try:
        db.session.commit()
        
        # Enviar e-mail diretamente
        try:
            body = f"OlÃ¡ {user.nome},\n\nUma nova senha temporÃ¡ria foi gerada conforme solicitado.\n\nSua senha temporÃ¡ria Ã©: {temp_pass}\n\nPor favor, altere-a no seu prÃ³ximo acesso."
            send_email_direct("Sua nova senha - PRP Financeiro", user.email, body)
            return {"success": True, "message": f"Nova senha enviada para {user.email}"}
        except Exception as e:
            from ..models import ConfiguracaoSMTP
            cfg = ConfiguracaoSMTP.query.first()
            host = cfg.smtp_server if cfg else "None"
            port = cfg.smtp_port if cfg else "None"
            debug_info = f" (Host: {host}:{port})"
            return {"success": False, "message": f"Erro ao enviar e-mail: {str(e)}{debug_info}. Senha gerada (para cÃ³pia manual): {temp_pass}"}, 400
            
    except Exception as e:
        db.session.rollback()
        return {"success": False, "message": f"Erro ao atualizar senha no banco: {str(e)}"}, 400

@auth_bp.route('/api/backup/export', methods=['GET'])
@login_required
def export_backup():
    if not current_user.is_admin:
        return {"success": False, "message": "Acesso negado."}, 403

    from ..config import Config
    db_url = _to_pg_tools_uri(Config.get_sqlalchemy_uri())

    temp_file = tempfile.NamedTemporaryFile(suffix='.backup', delete=False)
    temp_file.close()
    dump_path = temp_file.name

    try:
        pg_dump_bin = _resolve_pg_bin('pg_dump')
        cmd = [
            pg_dump_bin,
            '--dbname', db_url,
            '--format=custom',
            '--no-owner',
            '--no-privileges',
            '--verbose',
            '--file', dump_path,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            first_error = result.stderr or result.stdout or 'Falha no pg_dump'
            retry_db_url = _fallback_local_db_url(db_url, first_error)
            if retry_db_url and retry_db_url != db_url:
                cmd[2] = retry_db_url
                retry_result = subprocess.run(cmd, capture_output=True, text=True)
                if retry_result.returncode != 0:
                    raise Exception(retry_result.stderr or retry_result.stdout or first_error)
            else:
                raise Exception(first_error)

        with open(dump_path, 'rb') as f:
            memory_file = io.BytesIO(f.read())
        memory_file.seek(0)

        filename = f"backup_prp_dados_{datetime.now().strftime('%Y%m%d_%H%M%S')}.backup"
        return send_file(
            memory_file,
            mimetype='application/octet-stream',
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        current_app.logger.exception("Falha no export de backup PostgreSQL")
        if isinstance(e, FileNotFoundError):
            return {
                "success": False,
                "message": "Falha ao gerar backup: pg_dump nao encontrado no servidor. Configure PG_BIN_DIR (ou PG_DUMP_BIN) ou instale PostgreSQL Client Tools."
            }, 500
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

    temp_file = tempfile.NamedTemporaryFile(suffix='.backup', delete=False)
    temp_file.close()

    try:
        if not file.filename:
            raise Exception('Nome de arquivo invÃ¡lido.')

        filename = file.filename.lower()
        if not (filename.endswith('.backup') or filename.endswith('.dump') or filename.endswith('.sql')):
            raise Exception('Formato nao suportado. Envie um backup Postgres (.backup, .dump ou .sql).')

        file.save(temp_file.name)
        db_url = _to_pg_tools_uri(Config.get_sqlalchemy_uri())

        db.session.remove()
        db.engine.dispose()
        is_sql_backup = filename.endswith('.sql')
        if is_sql_backup:
            _truncate_public_tables_for_sql_restore()
            psql_bin = _resolve_pg_bin('psql')
            cmd = [
                psql_bin,
                '--dbname', db_url,
                '-v', 'ON_ERROR_STOP=1',
                '--single-transaction',
                '-f', temp_file.name,
            ]
        else:
            pg_restore_bin = _resolve_pg_bin('pg_restore')
            cmd = [
                pg_restore_bin,
                '--dbname', db_url,
                '--clean',
                '--if-exists',
                '--no-owner',
                '--no-privileges',
                '--single-transaction',
                '--verbose',
                temp_file.name,
            ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            first_error = result.stderr or result.stdout or ('Falha no psql' if is_sql_backup else 'Falha no pg_restore')
            retry_db_url = _fallback_local_db_url(db_url, first_error)
            if retry_db_url and retry_db_url != db_url:
                cmd[2] = retry_db_url
                retry_result = subprocess.run(cmd, capture_output=True, text=True)
                if retry_result.returncode != 0:
                    raise Exception(retry_result.stderr or retry_result.stdout or first_error)
            else:
                raise Exception(first_error)

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
        return {"success": False, "message": "Tema invÃ¡lido."}, 400
        
    current_user.tema = tema
    db.session.commit()
    return {"success": True, "tema": tema}



