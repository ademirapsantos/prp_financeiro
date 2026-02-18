from app import create_app
import sys

app = create_app()
app.config['TESTING'] = True
app.config['PROPAGATE_EXCEPTIONS'] = True

with app.app_context():
    try:
        from app.routes import main_bp
        with app.test_request_context('/'):
            response = main_bp.dashboard()
            print('Dashboard executado com sucesso!')
    except Exception as e:
        print(f'ERRO: {e}')
        import traceback
        traceback.print_exc()
