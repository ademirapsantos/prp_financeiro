from app import create_app
from app.models import db, ContaContabil, Titulo, LivroDiario, PartidaDiario, StatusTitulo, TipoTitulo
from datetime import datetime
from sqlalchemy import func
import os

app = create_app()

def diagnose_balancete():
    with app.app_context():
        output = []
        # Simulando o período padrão do balancete (mês atual)
        hoje = datetime.utcnow()
        data_inicio = hoje.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        data_fim = hoje.replace(hour=23, minute=59, second=59, microsecond=999999)

        output.append(f"Período: {data_inicio} até {data_fim}")

        # 1. Buscar todas as contas nível 1
        contas_nivel_1 = ContaContabil.query.filter(ContaContabil.codigo.notlike('%.%')).all()
        
        totais_reais = {}
        
        output.append("\n--- Balanço do Livro Diário (Toda a História) ---")
        for conta in contas_nivel_1:
            prefixo = conta.codigo
            res = db.session.query(
                func.sum(PartidaDiario.valor).filter(PartidaDiario.tipo == 'D').label('debitos'),
                func.sum(PartidaDiario.valor).filter(PartidaDiario.tipo == 'C').label('creditos')
            ).join(ContaContabil).filter(
                ContaContabil.codigo.like(f"{prefixo}%")
            ).first()
            
            debitos = res.debitos or 0
            creditos = res.creditos or 0
            
            if conta.natureza == 'Devedora':
                saldo = debitos - creditos
            else:
                saldo = creditos - debitos
            
            output.append(f"Conta {conta.codigo} ({conta.nome}): D={debitos:.2f}, C={creditos:.2f}, Saldo({conta.natureza})={saldo:.2f}")
            totais_reais[conta.codigo] = saldo

        # 2. Verificar Equação Fundamental: Ativo (1) = Passivo (2) + PL (3) + (Receita (4) - Despesa (5))
        ativo = totais_reais.get('1', 0)
        passivo = totais_reais.get('2', 0)
        pl_livro = totais_reais.get('3', 0)
        receita = totais_reais.get('4', 0)
        despesa = totais_reais.get('5', 0)
        
        balanco_patrimonial = ativo - (passivo + pl_livro)
        resultado = receita - despesa
        diferenca = balanco_patrimonial - resultado
        
        output.append(f"\n--- Verificação de Integridade (Ledger) ---")
        output.append(f"Ativo: {ativo:.2f}")
        output.append(f"Passivo: {passivo:.2f}")
        output.append(f"PL (No Livro): {pl_livro:.2f}")
        output.append(f"Receita: {receita:.2f}")
        output.append(f"Despesa: {despesa:.2f}")
        output.append(f"Resultado (Rec - Desp): {resultado:.2f}")
        output.append(f"Balanço (Ativo - Passivo - PL): {balanco_patrimonial:.2f}")
        output.append(f"Diferença Final: {diferenca:.2f} (Deveria ser zero)")

        # 3. Analisar a lógica especial do Grupo 3 (PL forcing)
        output.append("\n--- Lógica Especial Grupo 3 (Patrimônio Líquido) ---")
        res_ativos_fim = db.session.query(
            func.sum(PartidaDiario.valor).filter(PartidaDiario.tipo == 'D').label('debitos'),
            func.sum(PartidaDiario.valor).filter(PartidaDiario.tipo == 'C').label('creditos')
        ).join(ContaContabil).join(LivroDiario).filter(
            ContaContabil.codigo.like('1%'),
            ~ContaContabil.codigo.like('1.5%'),
            LivroDiario.data <= data_fim
        ).first()
        ativos_fim = (res_ativos_fim.debitos or 0) - (res_ativos_fim.creditos or 0)
        
        ap_fim = db.session.query(func.sum(Titulo.valor)).filter(
            Titulo.tipo == TipoTitulo.PAGAR.value,
            Titulo.status == StatusTitulo.ABERTO.value,
            Titulo.data_vencimento <= data_fim.date()
        ).scalar() or 0
        
        pl_calculado = ativos_fim - ap_fim
        output.append(f"Ativos (exceto 1.5) na data fim: {ativos_fim:.2f}")
        output.append(f"A Pagar (Títulos Abertos) na data fim: {ap_fim:.2f}")
        output.append(f"PL Calculado (Ativos - A Pagar): {pl_calculado:.2f}")
        output.append(f"PL no Livro Diário (Grupo 3): {pl_livro:.2f}")
        output.append(f"Diferença PL(Calc) vs PL(Livro): {pl_calculado - pl_livro:.2f}")

        # 4. Verificar o Grupo 1.5 (A Receber no Balanço)
        res_1_5 = db.session.query(
            func.sum(PartidaDiario.valor).filter(PartidaDiario.tipo == 'D').label('debitos'),
            func.sum(PartidaDiario.valor).filter(PartidaDiario.tipo == 'C').label('creditos')
        ).join(ContaContabil).filter(
            ContaContabil.codigo.like('1.5%')
        ).first()
        output.append(f"\nSaldo Conta 1.5 (Recebíveis no Ledger): {(res_1_5.debitos or 0) - (res_1_5.creditos or 0):.2f}")
        
        ar_total = db.session.query(func.sum(Titulo.valor)).filter(
            Titulo.tipo == TipoTitulo.RECEBER.value,
            Titulo.status == StatusTitulo.ABERTO.value
        ).scalar() or 0
        output.append(f"Total Títulos A Receber (Abertos): {ar_total:.2f}")

        with open('diagnose_output.txt', 'w', encoding='utf-8') as f:
            f.write("\n".join(output))

if __name__ == "__main__":
    diagnose_balancete()
