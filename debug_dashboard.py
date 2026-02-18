from app import create_app
import sys
import traceback

app = create_app()
app.config['TESTING'] = True
app.config['PROPAGATE_EXCEPTIONS'] = True

with app.app_context():
    try:
        # Importar a função dashboard diretamente
        from app.routes import dashboard
        from flask import Flask
        from werkzeug.test import EnvironBuilder
        from werkzeug.wrappers import Request
        
        # Criar um contexto de requisição falso
        with app.test_request_context('/'):
            result = dashboard()
            print("✅ Dashboard executado com sucesso!")
            print(f"Tipo de retorno: {type(result)}")
    except Exception as e:
        print(f"❌ ERRO DETALHADO:")
        print(f"Tipo: {type(e).__name__}")
        print(f"Mensagem: {str(e)}")
        print("\nTraceback completo:")
        traceback.print_exc()
