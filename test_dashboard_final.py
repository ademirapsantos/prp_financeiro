from app import create_app
import traceback

app = create_app()

with app.test_client() as client:
    try:
        response = client.get('/')
        print(f'Status Code: {response.status_code}')
        if response.status_code == 200:
            print('✅ Dashboard carregou com sucesso!')
        else:
            print('❌ Erro no Dashboard:')
            print(response.data.decode('utf-8')[:500])
    except Exception as e:
        print(f'❌ Exceção: {e}')
        traceback.print_exc()
