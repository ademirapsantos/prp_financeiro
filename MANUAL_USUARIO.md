# 📔 Guia Mestre do Usuário - PRP Financeiro

Bem-vindo ao nível avançado de gestão. O **PRP Financeiro** é uma ferramenta de alta precisão. Este guia expandido detalha fluxos complexos para que você tenha controle absoluto sobre seu patrimônio.

---

## 📑 1. Glossário Contábil (Para Não-Contadores)

Para dominar o sistema, entenda como o dinheiro se move:
*   **Ativo**: Tudo o que você tem (Dinheiro no banco, Carros, Imóveis, Ações).
*   **Passivo**: Tudo o que você deve (Empréstimos, Parcelas, Salários).
*   **DRE (Resultado)**: Onde você vê se teve lucro ou prejuízo (Receitas - Despesas).
*   **Partida Dobrada**: Se você compra um carro de R$ 50k, o sistema cria um Ativo (Carro) de +50k e um Passivo (Dívida) de -50k. O balanço sempre fecha.

---

## 🏢 2. Gestão de Ativos e Investimentos (O Coração do Patrimônio)

### 2.1. Ativos Imobilizados (Carros, Imóveis)
*   **Financiamento**: Ao comprar um imobilizado e escolher "Parcelado", o sistema faz 3 coisas:
    1.  Registra o bem no seu Ativo.
    2.  Cria os títulos no seu "Contas a Pagar".
    3.  Lança os **Juros** separadamente (caso informados), garantindo que o valor do bem seja o custo real e os juros sejam contabilizados como despesa financeira.
*   **Venda e Ganho de Capital**: Ao vender um imóvel por um valor maior do que você pagou, o sistema detecta a diferença e registra automaticamente um **"Ganho de Capital"** na sua contabilidade.

### 2.2. Investimentos (Ações, FIIs, Tesouro)
*   **Preço Médio**: O sistema não apenas soma valores, ele calcula o **Custo Médio Ponderado**. Se você comprou 10 ações a R$ 10 e depois 10 a R$ 20, seu custo médio é R$ 15.
*   **Venda Parcial**: Ao vender apenas 5 ações, o sistema baixa o Ativo pelo custo médio (R$ 15 cada) e o que você recebeu a mais (ou a menos) vira lucro ou prejuízo imediato.
*   **Estorno**: Errou o lançamento da compra? Use o botão **Estornar**. Ele apagará o ativo, os títulos e desfará o lançamento contábil, deixando tudo limpo.

---

## 👥 3. Entidades Inteligentes (Automatizando Lançamentos)

Cadastrar uma entidade corretamente é o "segredo" para que os lançamentos financeiros gerem a contabilidade exata sem que você precise ser um expert no assunto. No cadastro, você encontrará dois campos cruciais:

### 3.1. Conta Patrimonial (Balanço)
*   **O que é?** Representa o seu direito ou sua obrigação. É uma conta que "acumula" saldo no tempo.
*   **Para que serve?** Ela diz ao sistema *onde a dívida está pendente*.
    *   **Para Fornecedores**: Deve ser uma conta do tipo **Passivo** (ex: *Fornecedores a Pagar* ou *Empréstimos a Pagar*).
    *   **Para Clientes**: Deve ser uma conta do tipo **Ativo** (ex: *Clientes a Receber* ou *Vendas a Receber*).
*   **Na prática**: Quando você lança um boleto de R$ 100, este valor fica "estacionado" nesta conta patrimonial até o dia que você fizer o pagamento (liquidação).

### 3.2. Conta de Resultado (Categoria de Gasto/Ganho)
*   **O que é?** Representa a *natureza* do evento. É uma conta que indica de onde veio o lucro ou para onde foi o gasto.
*   **Para que serve?** Ela alimenta o seu relatório de Lucros e Perdas (DRE).
    *   **Para Fornecedores**: Deve ser uma conta de **Despesa** (ex: *Energia Elétrica*, *Aluguel*, *Manutenção*).
    *   **Para Clientes**: Deve ser uma conta de **Receita** (ex: *Receita de Serviços*, *Receita de Consultoria*).
*   **Na prática**: Ela explica *com o quê* o dinheiro foi gasto ou *de onde* ele veio.

### 3.3. Configuração para Entidades do tipo 'Outros'
Use este tipo para parceiros que podem ser tanto compradores quanto vendedores, ou para instituições financeiras.
*   **Conta de Venda (Ativo)**: Use uma conta de direito (ex: *Outros Valores a Receber*). Esta conta será usada quando você **vender** um ativo para esta entidade.
*   **Conta de Compra (Passivo)**: Use uma conta de obrigação (ex: *Contas a Pagar Diversas*). Esta conta será usada quando você **comprar** um bem desta entidade.

---

| Tipo de Entidade | Conta Patrimonial (Sugestão) | Conta de Resultado (Sugestão) |
| :--- | :--- | :--- |
| **Fornecedor** | Fornecedores a Pagar (Passivo) | Despesas Diversas (Despesa) |
| **Cliente** | Clientes a Receber (Ativo) | Receita de Vendas (Receita) |
| **Outros** | Contas a Receber/Pagar Diversas | (Configurável por transação) |

---

## 💰 4. Ciclo Financeiro e Conciliação

### 4.1. Provisão vs Liquidação (O Segredo da Organização)
Nunca pague uma conta sem antes "provisioná-la".
1.  **Lance o Título**: Registre a conta assim que ela chegar.
2.  **Liquide no Dia**: Só marque como pago no dia que o dinheiro sair do banco.
3.  **Transferências Entre Contas**: Use esta ferramenta para movimentar dinheiro entre Bancos (ex: Saque para o Caixa). Isso evita que você tenha que criar um título a pagar e outro a receber.

### 4.2. Fluxo de Caixa e Drilldown
No Dashboard, os gráficos são **vivos**. 
*   **Quer saber o que gastou em Maio?** Clique na barra azul de Maio. O sistema filtrará todos os títulos pagos naquele mês para você conferir item por item.

---

## 📊 5. Contabilidade para Auditoria

*   **Livro Diário**: É a sua bússola. Se você encontrar um erro, o ID do lançamento no Diário ajudará a localizar a transação original.
*   **Balancete Hierárquico**: Não olhe apenas para o saldo final. Use a expansão (setas) para entender quais subcontas estão consumindo seu orçamento.
*   **Exportação Excel**: Gere os relatórios no fim do mês e abra no Excel. Use filtros da planilha para fazer auditorias cruzadas com seus extratos físicos.

---

## 🛠️ 6. Resolução de Problemas (FAQ)

*   **"Meu título não aparece para liquidar!"**: Verifique o filtro de status (ele pode estar como 'Pago' ou 'Cancelado').
*   **"O saldo do meu banco está errado!"**: Confira se todas as transferências foram lançadas e se não há títulos liquidados na conta errada.
*   **"Fiz um lançamento errado, e agora?"**: Se for um título, você pode **Estornar**. Se for um ativo, o estorno reverte todas as parcelas de uma vez.
*   **"O Balancete não abre as contas!"**: Clique exatamente na seta ao lado do código da conta.

---

## � 7. Segurança de Dados e Backup

*   **Sessão Segura**: O "Bloqueio de Tela" é ideal para ambientes de escritório. Sua sessão continua ativa, mas os dados ficam ocultos.
*   **Backup Semanal**: Vá em **Configurações > Exportar Backup**. Baixe o arquivo e guarde em um local seguro (pendrive ou nuvem). Ele contém toda a sua vida financeira.

---

## 🚀 8. Guia de Implementação Rápida

Para quem está começando hoje:
1.  **Ajuste o Perfil**: Defina sua senha e tema.
2.  **Bancos**: Cadastre suas contas reais com o saldo atual.
3.  **Investimentos**: Lance sua carteira atual como se fosse uma nova compra hoje.
4.  **Imóveis/Carros**: Lance seus bens atuais para ter o Patrimônio Líquido correto no Balancete.

---

*PRP Financeiro - Projetado para a clareza, construído para a precisão.*
