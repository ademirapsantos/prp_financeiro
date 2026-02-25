# Manual do Usuário - PRP Financeiro

## Índice

1. [Apresentação do Sistema](#1-apresentacao-do-sistema)
2. [Navegação Geral](#2-navegacao-geral)
3. [Módulos Detalhados](#3-modulos-detalhados)
4. [Operações Passo a Passo](#4-operacoes-passo-a-passo)
5. [Boas Práticas](#5-boas-praticas)

## 1. Apresentação do Sistema {#1-apresentacao-do-sistema}

### 1.1 Finalidade

O PRP Financeiro é um sistema web para gestão financeira e contábil integrada, com controle de:

- contas a pagar e a receber (títulos);
- liquidação e estorno com rastreabilidade;
- plano de contas e parâmetros contábeis;
- ativos (bens, bancos/caixa e investimentos);
- cartões de crédito e faturas;
- relatórios contábeis (Livro Diário e Balancete).

O sistema registra eventos financeiros com reflexo no Livro Diário por partidas dobradas, respeitando regras de natureza contábil e contas analíticas.

### 1.2 Público-alvo

- usuários operacionais financeiros (lançamentos, liquidação, conferência);
- gestores (acompanhamento de posição financeira e indicadores);
- contabilidade interna (balancete, diário, consistência de contas);
- administradores do sistema (usuários, SMTP, backup/restore e atualização).

### 1.3 Conceito contábil adotado

O sistema opera com lógica de competência para geração e manutenção de títulos (contas a pagar/receber) e reconhece a movimentação de caixa/bancos no momento da liquidação. Na prática operacional:

- criação de título gera obrigação/direito em aberto;
- liquidação baixa o título e registra movimentação financeira com lançamentos contábeis;
- estorno executa reversões com regras de segurança temporal.

### 1.4 Arquitetura resumida (App + Banco + Updater)

- App: aplicação Flask (web + regras de negócio + templates).
- Banco: PostgreSQL.
- Updater: serviço HTTP separado para atualização controlada da aplicação, com lock, backup, health check e rollback.

## 2. Navegação Geral {#2-navegacao-geral}

### 2.1 Estrutura da interface

A navegação principal é organizada por módulos funcionais, incluindo:

- Dashboard;
- Financeiro;
- Contabilidade;
- Entidades;
- Ativos;
- Plano de Contas;
- Administração (usuários, SMTP, backup/restore, bloqueio de tela, senha).

### 2.2 Conceito de módulos

Cada módulo concentra um domínio:

- Financeiro: ciclo de títulos, liquidação, estorno, bancos/cartões.
- Contabilidade: diário, balancete, parâmetros e visões analíticas.
- Cadastros base: entidades, ativos e contas contábeis.

## 3. Módulos Detalhados {#3-modulos-detalhados}

### 3.1 Dashboard

Finalidade:

- apresentar visão consolidada de receitas, despesas, saldos e indicadores do período.

Quando usar:

- monitoramento gerencial diário e fechamento mensal.

Relação com outros módulos:

- consolida dados de títulos, diário e cartões/faturas.

Particularidades:

- possui APIs de drilldown e leitura de métricas.

Restrições:

- depende de parametrização contábil e lançamentos existentes.

Impacto contábil:

- não gera lançamento; apenas consulta/analisa dados já registrados.

### 3.2 Financeiro

Finalidade:

- gerir contas a receber/pagar, liquidações, estornos, transferências, bancos e cartões.

Quando usar:

- operação diária de caixa e contas.

Relação com outros módulos:

- utiliza Entidades, Ativos (bancos/caixa), Plano de Contas e Contabilidade.

Particularidades:

- títulos em abas de pendentes/pagas;
- filtros por período, tipo e entidade;
- bloqueios de estorno por prazo;
- ação “Copiar” disponível apenas para títulos pagos.

Restrições:

- liquidação exige conta bancária/caixa;
- cópia bloqueada para título não pago;
- estorno bloqueado quando ultrapassados limites de 20 dias (título pago) e 60 dias (emissão).

Impacto contábil:

- criação de título: registro de obrigação/direito em aberto;
- liquidação: baixa financeira e contábil;
- estorno: reversão de baixa e cancelamento.

### 3.3 Contabilidade

Finalidade:

- consulta e exportação do Livro Diário e Balancete;
- configuração de parâmetros contábeis.

Quando usar:

- conferência contábil, auditoria e fechamento.

Relação com outros módulos:

- recebe lançamentos de financeiro, ativos e cartões.

Particularidades:

- exportação para Excel em Diário e Balancete.

Restrições:

- depende da integridade do plano de contas e das partidas.

Impacto contábil:

- módulo de consulta e parametrização; não cria títulos diretamente.

### 3.4 Entidades

Finalidade:

- cadastro de cliente, fornecedor e outros.

Quando usar:

- antes de gerar títulos, compras, vendas e operações correlatas.

Relação com outros módulos:

- títulos e ativos dependem de entidade vinculada;
- mapeamento de contas por tipo de entidade.

Particularidades:

- campos de conta de compra/venda variam conforme tipo da entidade.

Restrições:

- para operações financeiras completas, entidade precisa ter contas compatíveis.

Impacto contábil:

- cadastro em si não lança diário; influencia lançamentos futuros.

### 3.5 Ativos

Finalidade:

- registrar ativos (incluindo banco/caixa e investimentos), compra, venda e recompra.

Quando usar:

- controle patrimonial e financeiro de ativos.

Relação com outros módulos:

- bancos/caixa são usados na liquidação de títulos;
- compras/vendas geram títulos e lançamentos.

Particularidades:

- sincroniza `valor_atual` pelo saldo real da conta contábil no diário.

Restrições:

- venda/recompra seguem regras por tipo do ativo.

Impacto contábil:

- operações em ativos refletem no patrimônio, resultado e financeiro conforme a natureza do evento.

### 3.6 Plano de Contas

Finalidade:

- manter contas contábeis com código, tipo, natureza e hierarquia.

Quando usar:

- implantação e manutenção contábil do sistema.

Relação com outros módulos:

- base para lançamentos em todos os fluxos financeiros/contábeis.

Particularidades:

- prevenção de duplicidade de código por restrição de integridade.

Restrições:

- contas analíticas são exigidas nas rotinas de lançamento.

Impacto contábil:

- estruturação correta determina consistência de diário e balancete.

### 3.7 Administração

Finalidade:

- autenticação, usuários, troca de senha, bloqueio de tela, SMTP, backup/restore.

Quando usar:

- governança de acesso e operação de manutenção.

Relação com outros módulos:

- transversal a toda aplicação.

Particularidades:

- API de tema da interface;
- endpoints de backup e restauração.

Restrições:

- ações administrativas requerem autenticação e permissões.

Impacto contábil:

- sem impacto direto de lançamento, mas afeta continuidade operacional e segurança.

## 4. Operações Passo a Passo {#4-operacoes-passo-a-passo}

### 4.1 Criar Título (Receita)

O que o usuário faz:

1. Acessa `Financeiro > + Nova Venda`.
2. Informa cliente, descrição, valor e vencimento.
3. Clica em `Registrar Venda`.

O que o sistema faz:

1. Valida dados enviados.
2. Busca a entidade cliente.
3. Executa criação de título a receber (`Tipo = Receber`, `Status = Aberto`).
4. Persiste o novo registro e retorna mensagem de sucesso.

Impacto contábil:

- cria direito a receber em aberto para posterior baixa/liquidação.

O que não pode ser feito:

- registrar sem cliente válido;
- registrar com dados obrigatórios ausentes.

### 4.2 Criar Título (Despesa)

O que o usuário faz:

1. Acessa `Financeiro > + Novo Pagamento`.
2. Informa fornecedor, descrição, valor e vencimento.
3. Clica em `Registrar Pagamento`.

O que o sistema faz:

1. Valida dados enviados.
2. Busca a entidade fornecedora.
3. Executa criação de título a pagar (`Tipo = Pagar`, `Status = Aberto`).
4. Persiste o novo registro e retorna mensagem de sucesso.

Impacto contábil:

- cria obrigação a pagar em aberto para posterior baixa/liquidação.

O que não pode ser feito:

- registrar sem fornecedor válido;
- registrar com dados obrigatórios ausentes.

### 4.3 Liquidar Título

O que o usuário faz:

1. Na lista de títulos pendentes, clica em `Liquidar`.
2. Informa conta bancária/caixa, data de pagamento e desconto (quando aplicável).
3. Confirma a liquidação.

O que o sistema faz:

1. Valida existência do título e da conta financeira.
2. Executa rotina de liquidação financeira.
3. Atualiza status do título para pago, grava data de liquidação.
4. Registra transação financeira de baixa.
5. Registra lançamentos contábeis correspondentes no diário.

Impacto contábil:

- baixa obrigação/direito e reconhece movimento em banco/caixa.

O que não pode ser feito:

- liquidar sem banco/caixa cadastrado;
- liquidar título inexistente.

### 4.4 Editar Título

Situação atual implementada:

- não existe rota/tela dedicada para edição direta de título já cadastrado.
- o sistema atual oferece criação, liquidação, estorno e cópia (para título pago).

Orientação operacional:

- para ajuste de dados, utiliza-se o fluxo operacional existente conforme caso (novo lançamento, liquidação, estorno, cópia).

### 4.5 Copiar Título Pago

O que o usuário faz:

1. Na aba de títulos pagos, clica em `Copiar`.
2. É redirecionado para `Nova Venda` (se origem for Receber) ou `Novo Pagamento` (se origem for Pagar).
3. Revisa campos pré-preenchidos.
4. Salva para criar novo título.

O que o sistema faz:

1. Valida que o título existe.
2. Valida que o status é `Pago`.
3. Monta valores padrão com base no título original:
   - entidade;
   - descrição;
   - valor;
   - data de vencimento;
   - referência interna de origem (`copied_from_id`) para controle de UI.
4. Redireciona para o formulário de novo título com defaults.
5. Ao salvar, cria novo título (novo UUID) em aberto.

Impacto contábil:

- a ação de “copiar” não replica baixa nem transações financeiras do título de origem;
- impacto contábil ocorre somente quando o novo título for liquidado.

O que não pode ser feito:

- copiar título em aberto ou cancelado;
- usar o fluxo de cópia para alterar o título original.

### 4.6 Criar Entidade

O que o usuário faz:

1. Acessa `Entidades > Nova`.
2. Informa nome, tipo, documento e contas conforme tipo.
3. Salva cadastro.

O que o sistema faz:

1. Cria nova entidade com campos de conta conforme regra do tipo:
   - fornecedor: conta de compra;
   - cliente: conta de venda;
   - outros: conta de compra e venda.
2. Persiste no banco e retorna sucesso.

Impacto contábil:

- sem lançamento imediato; habilita consistência de lançamentos futuros.

O que não pode ser feito:

- depender de mapeamento contábil inexistente para fluxos que exigem conta vinculada.

### 4.7 Criar Ativo

O que o usuário faz:

1. Acessa `Ativos > Novo`.
2. Informa dados do ativo e fornecedor.
3. Seleciona tipo do ativo e conta contábil.
4. Salva.

O que o sistema faz:

1. Para investimento: executa compra de investimento com regras específicas.
2. Para demais tipos: executa compra de imobilizado, podendo gerar parcelamento.
3. Registra eventos financeiros/contábeis conforme serviço de ativos.

Impacto contábil:

- reconhecimento patrimonial do ativo e obrigações/direitos correlatos.

O que não pode ser feito:

- concluir compra com dados essenciais ausentes.

### 4.8 Configurar Parâmetros Contábeis

O que o usuário faz:

1. Acessa área de contabilidade/configuração.
2. Define contas de parâmetros usadas pelas rotinas contábeis.
3. Salva parâmetros.

O que o sistema faz:

1. Persiste configurações globais.
2. Passa a utilizar esses vínculos nas rotinas automáticas de lançamento.

Impacto contábil:

- altera o destino contábil dos lançamentos futuros.

O que não pode ser feito:

- esperar consistência contábil sem parametrização adequada.

### 4.9 Gerar Relatórios

Relatórios implementados:

- Livro Diário (`/contabilidade/diario` + exportação Excel);
- Balancete (`/contabilidade/balancete` + exportação Excel).

O que o usuário faz:

1. Seleciona período.
2. Consulta dados.
3. Exporta para `.xlsx` quando necessário.

O que o sistema faz:

1. Executa consultas por período.
2. Consolida saldos/debitos/créditos conforme regra de cada relatório.
3. Gera arquivo de exportação.

Impacto contábil:

- não altera dados; evidencia a escrituração já registrada.

O que não pode ser feito:

- gerar resultado consistente sem base de lançamentos válida no período.

## 5. Boas Práticas {#5-boas-praticas}

### 5.1 Organização financeira

- padronizar descrições/históricos para facilitar auditoria;
- manter entidades e contas atualizadas antes dos lançamentos;
- revisar títulos em aberto por vencimento.

### 5.2 Uso correto de categorias e contas

- usar contas analíticas para operações que geram lançamento;
- evitar uso de contas incompatíveis com a natureza da operação.

### 5.3 Uso correto de regime

- tratar criação de título como reconhecimento de obrigação/direito;
- tratar liquidação como baixa financeira efetiva.

### 5.4 Cuidados ao liquidar títulos

- conferir banco/caixa selecionado e data de pagamento;
- validar desconto aplicado;
- evitar liquidação duplicada do mesmo título.

### 5.5 Evitar distorções no balancete

- não misturar contas de natureza distinta;
- manter plano de contas coerente (código, tipo, natureza);
- usar estorno apenas dentro das regras temporais implementadas.
