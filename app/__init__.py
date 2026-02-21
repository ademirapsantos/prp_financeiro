from flask import Flask, render_template, redirect, url_for, request, session
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from flask_login import LoginManager, current_user
from flask_mail import Mail
import os
from .version import __version__, __build__

db = SQLAlchemy()
mail = Mail()

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'dev_key_prp_system'
    
    # ConfiguraÃ§Ã£o centralizada de caminhos
    from .config import Config
    app.config['SQLALCHEMY_DATABASE_URI'] = Config.get_sqlalchemy_uri()
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['__version__'] = __version__
    app.config['__build__'] = __build__

    # Flask-Mail base config (Os valores reais virÃ£o do DB)
    from .models import ConfiguracaoSMTP
    with app.app_context():
        try:
            cfg = ConfiguracaoSMTP.query.first()
            if cfg:
                app.config['MAIL_SERVER'] = cfg.smtp_server
                app.config['MAIL_PORT'] = int(cfg.smtp_port)
                app.config['MAIL_USE_TLS'] = cfg.use_tls
                app.config['MAIL_USE_SSL'] = cfg.use_ssl
                app.config['MAIL_USERNAME'] = cfg.smtp_user
                app.config['MAIL_PASSWORD'] = cfg.smtp_password
        except:
            pass # Fallback se o banco nÃ£o estiver pronto

    db.init_app(app)
    mail.init_app(app)

    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Por favor, faÃ§a login para acessar esta pÃ¡gina.'
    login_manager.login_message_category = 'info'
    login_manager.init_app(app)

    app.jinja_env.globals["APP_VERSION"] = __version__
    app.jinja_env.globals["APP_BUILD"] = __build__

    @login_manager.unauthorized_handler
    def unauthorized():
        if request.path.startswith('/api/'):
            return {"error": "unauthorized"}, 401
        return redirect(url_for('auth.login'))

    @login_manager.user_loader
    def load_user(user_id):
        from .models import User
        return User.query.get(user_id)

    with app.app_context():
        from . import models
        db.create_all()
        
        # MigraÃ§Ãµes defensivas (Schema update)
        from .migrations import run_migrations
        try:
            run_migrations()
        except Exception as e:
            app.logger.error(f"Falha crÃ­tica nas migraÃ§Ãµes: {e}")

        # Importante: Criar plano de contas inicial se nÃ£o existir
        from .seed import seed_db
        seed_db()

    from .routes import main_bp
    app.register_blueprint(main_bp)

    from .routes_entidades import entidades_bp
    app.register_blueprint(entidades_bp)

    from .routes_ativos import ativos_bp
    app.register_blueprint(ativos_bp)

    from .routes_financeiro import financeiro_bp
    app.register_blueprint(financeiro_bp)

    from .routes_contas import contas_bp
    app.register_blueprint(contas_bp)

    from .auth import auth_bp
    app.register_blueprint(auth_bp)

    # ProteÃ§Ã£o Global de Rotas
    @app.before_request
    def check_auth():
        from .models import User
        from flask import session
        

        # Endpoints de orquestracao devem ser publicos por path.
        public_paths = {
            '/health',
            '/api/system/update/status',
            '/api/system/latest',
            '/api/version',
            '/api/system/maintenance/off-token',
            '/api/system/update/finalize-token'
        }
        if request.path in public_paths:
            return

        # Permitir acesso a rotas estÃ¡ticas, blueprint de auth e endpoints pÃºblicos de sistema
        public_endpoints = [
            'main.api_version',
            'main.system_latest',
            'main.health',
            'main.api_system_update_status',
            'main.maintenance_off_token',
            'main.api_system_update_finalize_token'
        ]
        if request.endpoint and (
            'static' in request.endpoint or 
            'auth' in request.endpoint or
            request.endpoint in public_endpoints
        ):
            # Se tentar acessar login/register estando bloqueado, redirecionar para lock_screen
            if session.get('is_locked') and request.endpoint not in ['auth.lock_screen', 'auth.logout', 'static']:
                return redirect(url_for('auth.lock_screen'))
            return

        # Se nÃ£o houver usuÃ¡rios no banco, permitir apenas acesso ao registro inicial
        user_count = User.query.count()
        if user_count == 0:
            if request.endpoint != 'auth.register':
                return redirect(url_for('auth.register'))
            return

        # Bloquear acesso se nÃ£o estiver logado
        if not current_user.is_authenticated:
            # Se for API, o unauthorized_handler cuidarÃ¡ disso se usarmos login_required,
            # mas aqui Ã© uma proteÃ§Ã£o global. Vamos garantir que APIs retornem JSON.
            if request.path.startswith('/api/'):
                return {"error": "unauthorized"}, 401
            return redirect(url_for('auth.login'))
        
        # Bloquear se o sistema estiver em estado de "Bloqueio"
        if session.get('is_locked') and request.endpoint != 'auth.lock_screen' and request.endpoint != 'auth.logout':
            return redirect(url_for('auth.lock_screen'))
        
        # ForÃ§ar troca de senha se necessÃ¡rio
        if current_user.deve_alterar_senha and request.endpoint != 'auth.change_password' and request.endpoint != 'auth.logout' and not session.get('is_locked'):
            return redirect(url_for('auth.change_password'))

    # Context processor para notificaÃ§Ãµes globais
    @app.context_processor
    def inject_notifications():
        from .models import Titulo, StatusTitulo, Notificacao
        from datetime import datetime, timedelta

        hoje = datetime.utcnow().date()
        proximos_dias = hoje + timedelta(days=3)

        # NotificaÃ§Ãµes de TÃ­tulos (Urgentes)
        notificacoes_financeiras = Titulo.query.filter(
            Titulo.status == StatusTitulo.ABERTO.value,
            Titulo.data_vencimento <= proximos_dias,
            Titulo.data_vencimento >= hoje
        ).order_by(Titulo.data_vencimento.asc()).all()

        # NotificaÃ§Ãµes de Sistema (NÃ£o lidas)
        notificacoes_sistema = []
        if current_user.is_authenticated:
            notificacoes_sistema = Notificacao.query.filter(
                (Notificacao.user_id == current_user.id) | (Notificacao.user_id == None)
            ).filter_by(lida=False).order_by(Notificacao.criada_em.desc()).all()

        return dict(
            notificacoes_alert=notificacoes_financeiras,
            notificacoes_sistema=notificacoes_sistema
        )


    return app
