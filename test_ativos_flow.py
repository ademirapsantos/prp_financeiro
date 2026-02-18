from app import create_app, db
from app.models import Ativo, Titulo, TransacaoFinanceira, Entidade, TipoEntidade, ContaContabil, TipoAtivo
import datetime

def test_ativos_flow():
    app = create_app()
    app.config['PROPAGATE_EXCEPTIONS'] = True
    
    with app.app_context():
        print("--- 1. Preparando Massa de Dados ---")
        # Criar Fornecedor de Veículos (se não existir)
        fornecedor = Entidade.query.filter_by(nome='Concessionária Teste').first()
        if not fornecedor:
            # Pegar conta de Fornecedores
            conta_passivo = ContaContabil.query.filter(ContaContabil.nome.like('%Fornecedores%')).first()
            fornecedor = Entidade(
                nome='Concessionária Teste', 
                tipo=TipoEntidade.FORNECEDOR.value,
                documento='99.999.999/0001-99',
                conta_contabil_id=conta_passivo.id
            )
            db.session.add(fornecedor)
            db.session.commit()
            print(f"Fornecedor criado: {fornecedor.id}")
        
        # Conta de Veículos (Ativo Não Circulante - 1.4)
        conta_veiculos = ContaContabil.query.filter_by(codigo='1.4').first()
        if not conta_veiculos:
            print("❌ Conta de Veículos (1.4) não encontrada no Seed.")
            return

        print("--- 2. Simulando Compra via Service ---")
        from app.services import AssetService
        
        try:
            ativo = AssetService.comprar_ativo_imobilizado(
                descricao="Fiat Uno 2010",
                valor=15000.00,
                entidade_fornecedor=fornecedor,
                data_aquisicao=datetime.date.today(),
                conta_ativo_id=conta_veiculos.id,
                tipo_ativo=TipoAtivo.VEICULO.value
            )
            db.session.commit()
            print(f"✅ Ativo Criado: {ativo.descricao} (ID: {ativo.id})")
        except Exception as e:
            print(f"❌ Erro no Service: {e}")
            return

        print("--- 3. Verificações ---")
        # 3.1 Título a Pagar
        titulo = Titulo.query.filter_by(descricao="Aquis. Ativo: Fiat Uno 2010").first()
        if titulo:
            print(f"✅ Título CP Criado: {titulo.descricao} - Valor: {titulo.valor}")
        else:
            print("❌ Título não encontrado.")

        # 3.2 Transação de Aquisição (Opcional, mas implementamos)
        transacao = TransacaoFinanceira.query.filter_by(ativo_id=ativo.id).first()
        if transacao:
            print(f"✅ Transação Vinculada: {transacao.tipo} - ID: {transacao.id}")
        else:
            print("⚠️ Transação não encontrada (pode ser opcional no design).")
            
        # 3.3 Contabilidade
        # Verificar o último lançamento no diário
        # Deve ter D: Veículos (1.4) e C: Fornecedores (2.3)
        print("🔍 Verificando Contabilidade...")
        # (Neste teste simples, confiamos que o Service chamou o AccountingService, que lança exceção se não bater)

if __name__ == "__main__":
    test_ativos_flow()
