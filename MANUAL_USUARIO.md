# 📔 Manual Técnico e Funcional - PRP Financeiro

Este manual detalha o funcionamento do sistema, com foco especial na sua **Inteligência Contábil**. O PRP Financeiro utiliza o método de **Partidas Dobradas**, garantindo que cada transação financeira gere registros automáticos e equilibrados no Livro Diário.

---

## 📑 1. Fundamentos Contábeis do Sistema

Para entender o sistema, você deve conhecer como as contas são classificadas. O Plano de Contas é dividido em 5 grupos principais:

| Grupo | Tipo | Natureza | Exemplo | Comportamento |
| :--- | :--- | :--- | :--- | :--- |
| **1** | **Ativo** | Devedora | Banco, Imóveis | Aumenta com Débito / Diminui com Crédito |
| **2** | **Passivo** | Credora | Fornecedores, Empréstimos | Aumenta com Crédito / Diminui com Débito |
| **3** | **Patrimônio** | Credora | Capital Social | Representa a riqueza líquida acumulada. |
| **4** | **Receita** | Credora | Vendas, Rendimentos | Sempre lançada a Crédito (gera lucro). |
| **5** | **Despesa** | Devedora | Aluguel, Salários | Sempre lançada a Débito (gera perda). |

> [!IMPORTANT]
> **A Equação Fundamental**: Ativo = Passivo + Patrimônio Líquido + (Receitas - Despesas).
> O sistema garante que os **Débitos** sejam sempre iguais aos **Créditos** em cada operação.

---

## 💸 2. Ciclo Financeiro: Como os Lançamentos Funcionam

O sistema opera prioritariamente em **Regime de Caixa** para a DRE, mas mantém o controle patrimonial constante.

### 2.1. Lançamento de Títulos (Provisão)
Ao cadastrar um título (Pagar ou Receber), o sistema gera um registro financeiro para controle de vencimento. A contabilização real, no entanto, ocorre no momento da **Liquidação**.

### 2.2. Liquidação (Pagamento ou Recebimento)
Este é o momento onde o dinheiro "troca de mãos" contabilmente.

*   **Ao Pagar uma Conta**:
    *   **Débito**: Conta de Despesa (ex: Energia Elétrica - Grupo 5) -> *Reconhece o gasto.*
    *   **Crédito**: Conta de Ativo (ex: Banco Itaú - Grupo 1) -> *Registra a saída do dinheiro.*
*   **Ao Receber um Valor**:
    *   **Débito**: Conta de Ativo (ex: Banco - Grupo 1) -> *Registra a entrada do dinheiro.*
    *   **Crédito**: Conta de Receita (ex: Vendas - Grupo 4) -> *Reconhece o ganho.*

---

## 🏢 3. Gestão de Ativos e Investimentos

O sistema possui uma lógica sofisticada para bens duráveis e ativos financeiros.

### 3.1. Compra de Ativos (Carros, Imóveis)
Ao comprar um ativo parcelado:
1.  **Imobilização**: O sistema cria o registro do bem pelo valor principal.
2.  **Parcelamento**: Gera títulos no "Contas a Pagar".
3.  **Liquidação de Parcela**:
    *   **Débito**: Conta do Ativo (ex: Veículos) -> *O bem "ganha" valor conforme você paga.*
    *   **Crédito**: Conta de Banco -> *Saída do dinheiro.*

### 3.2. Investimentos (Ações, Tesouro)
O sistema gerencia o **Custo Médio Ponderado**.
*   **Compra**: D: Investimentos (Balanço) / C: Banco.
*   **Venda (Com Lucro)**:
    *   **Débito**: Banco (Valor Total Recebido).
    *   **Crédito**: Investimentos (Baixa pelo Custo Médio).
    *   **Crédito**: **Ganho de Capital (Receita)** -> *A diferença entra como lucro líquido.*

---

## 👥 4. Configuração de Entidades (O Cérebro da Automação)

Para que o sistema saiba quais contas usar, cada "Pessoa" (Cliente/Fornecedor) deve ser configurada:

1.  **Conta Patrimonial**: Onde a dívida "mora" (ex: Fornecedores a Pagar).
2.  **Conta de Resultado**: O que aquele gasto representa (ex: Despesa com Manutenção).

> [!TIP]
> Use entidades do tipo **'Outros'** para bancos ou parceiros de empréstimos. Nelas, você define contas separadas para fluxos de entrada (tomar empréstimo) e saída (conceder empréstimo).

---

## 📊 5. Relatórios e Auditoria

### 5.1. Livro Diário
O histórico cronológico de tudo. Cada linha possui um ID de transação. Se algo parecer estranho no balancete, localize o ID no Diário para ver exatamente quais contas foram debitadas e creditadas.

### 5.2. Balancete de Verificação
O balancete agora possui um **Validador de Equilíbrio**.
*   Se o rodapé estiver **Verde**, significa que todos os lançamentos de débito e crédito no período estão equilibrados.
*   As contas são exibidas em árvore. As contas de nível superior (ex: 1. ATIVO) somam automaticamente os saldos de todas as subcontas.

---

## 🛠️ 6. Resolução de Problemas Comuns

*   **"Diferença no Balancete"**: O sistema impede lançamentos manuais desequilibrados, mas se houver diferença, verifique se houve algum estorno parcial de transações complexas.
*   **"Custo Médio de Investimentos zerado"**: Ocorre se você tentar registrar uma venda antes de registrar a compra inicial. Sempre siga a ordem cronológica.

---
*PRP Financeiro - Precisão Contábil, Controle Absoluto.*
