from app import create_app
from app.routes import get_balancete_results
from datetime import datetime

app = create_app()

def test_final_balancete():
    with app.app_context():
        hoje = datetime.utcnow()
        data_inicio = hoje.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        data_fim = hoje.replace(hour=23, minute=59, second=59, microsecond=999999)

        results = get_balancete_results(data_inicio, data_fim)
        
        total_debitos = 0
        total_creditos = 0
        
        print(f"--- Balancete Results (Nível 1) ---")
        for item in results:
            if item['nivel'] == 1:
                print(f"Conta {item['codigo']} ({item['nome']}): D={item['debitos']:.2f}, C={item['creditos']:.2f}, Natureza={item['natureza']}")
                total_debitos += item['debitos']
                total_creditos += item['creditos']
        
        print(f"\nTotal Débitos: {total_debitos:.2f}")
        print(f"Total Créditos: {total_creditos:.2f}")
        print(f"Diferença: {total_debitos - total_creditos:.2f}")
        
        if abs(total_debitos - total_creditos) < 0.01:
            print("\nRESULTADO: ✅ Balancete Equilibrado!")
        else:
            print("\nRESULTADO: ❌ Inconsistência detectada!")

if __name__ == "__main__":
    test_final_balancete()
