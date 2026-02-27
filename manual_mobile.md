# Manual do App Mobile - PRP Mobile

## Indice

1. [Apresentacao](#1-apresentacao)
2. [Acesso e Login](#2-acesso-e-login)
3. [Navegacao Principal](#3-navegacao-principal)
4. [Dashboard](#4-dashboard)
5. [Contas a Pagar](#5-contas-a-pagar)
6. [Faturas](#6-faturas)
7. [Dividas](#7-dividas)
8. [Tema e Biometria](#8-tema-e-biometria)
9. [Boas Praticas](#9-boas-praticas)
10. [FAQ e Solucao de Problemas](#10-faq-e-solucao-de-problemas)

---

## 1. Apresentacao

O **PRP Mobile** e o cliente mobile oficial do sistema **PRP Financeiro**.

Objetivo do app:

- consultar indicadores financeiros de forma rapida;
- acompanhar contas a pagar, faturas e dividas;
- registrar lancamentos de forma agil no dia a dia.

Importante:

- o app mobile **nao altera regras contabeis** do sistema;
- liquidacao, baixa contabil e rotinas pesadas permanecem no fluxo web;
- o mobile reaproveita APIs e validacoes do backend oficial.

---

## 2. Acesso e Login

### 2.1 Login com email e senha

1. Abra o app.
2. Informe `Email` e `Senha`.
3. Toque em `Entrar`.

Validacoes:

- se email/senha estiverem vazios: mensagem `Informe email e senha.`
- se credenciais estiverem invalidas: mensagem `Email ou senha incorretos.`

### 2.2 Login com biometria

Pre-requisitos:

- ja ter feito login ao menos uma vez com sucesso;
- biometria ativada no app;
- biometria disponivel no dispositivo.

Fluxo:

1. Na tela de login, toque em `Entrar com biometria`.
2. Confirme sua biometria no sistema operacional.
3. O app entra com a sessao salva.

---

## 3. Navegacao Principal

A navegacao inferior possui 4 abas:

1. `Dashboard`
2. `Contas a Pagar`
3. `Faturas`
4. `Dividas`

No cabecalho superior:

- seletor de `Tema` (claro/escuro);
- atalho de `Biometria` (ativar/desativar);
- botao `Sair`.

---

## 4. Dashboard

O Dashboard possui:

- seletor de mes (lookup de Janeiro a Dezembro);
- card `Total Pendente (Cartoes)`;
- card `Total Despesas no Mes`;
- lista `Proximos Vencimentos`.

### 4.1 Regra do filtro de mes

O mes selecionado afeta:

- `Total Pendente (Cartoes)`
- `Total Despesas no Mes`

Nao afeta:

- `Proximos Vencimentos` (segue regra propria de exibicao de vencidos e a vencer).

### 4.2 Detalhamento dos cards

Ao tocar em um card de total:

- abre tela com os registros que compoem o valor;
- exibe total consolidado no rodape;
- possui botao `Voltar`.

---

## 5. Contas a Pagar

A tela `Contas a Pagar` exibe **somente**:

- Titulos com `Tipo = Pagar`
- `Status = Aberto`
- `Data de vencimento >= hoje`

Ou seja, mostra contas abertas dentro do prazo (inclui vencimento de hoje).

### 5.1 Novo Lancamento

Toque no botao `Novo` para abrir o formulario.

Campos principais:

- Descricao
- Valor
- Data do lancamento
- Meio (`Cartao` ou `Conta`)

#### 5.1.1 Quando Meio = Cartao

- Data fica bloqueada;
- data usada no lancamento = data atual de criacao;
- obrigatorio informar:
  - Cartao
  - Categoria

#### 5.1.2 Quando Meio = Conta

- Data obrigatoria (selecionada no campo de data);
- obrigatorio informar:
  - Tipo (`Despesa/Pagar` ou `Receita/Receber`)
  - Entidade compativel

Comportamento contabil no mobile para `Meio = Conta`:

- cria titulo (nao liquida);
- nao movimenta saldo de banco no app;
- liquidacao continua no fluxo web.

### 5.2 Atualizacao de dados

Apos salvar um lancamento com sucesso:

- lista de `Contas a Pagar` e atualizada;
- `Dashboard` tambem e atualizado automaticamente.

---

## 6. Faturas

A tela `Faturas` exibe:

- cartoes ativos;
- faturas abertas/pendentes;
- valores e vencimentos para acompanhamento.

Uso principal:

- monitoramento de limite e pendencias de cartao.

---

## 7. Dividas

A tela `Dividas` exibe **somente**:

- Titulos com `Tipo = Pagar`
- `Status = Aberto`
- `Data de vencimento < hoje`

Ou seja, apenas itens vencidos e ainda em aberto.

---

## 8. Tema e Biometria

### 8.1 Tema (Claro/Escuro)

No cabecalho, use o menu de tema para alternar:

- `Tema claro`
- `Tema escuro`

Persistencia:

- a escolha fica salva no dispositivo;
- ao reabrir o app, o tema selecionado e reaplicado.

### 8.2 Biometria

No cabecalho, use o icone de digital:

- `fingerprint_outlined`: biometria desativada
- `fingerprint`: biometria ativada

Ativar biometria:

1. toque no icone;
2. confirme biometria no dispositivo;
3. o app salva a preferencia.

Desativar biometria:

1. toque novamente no icone;
2. app desativa o recurso localmente.

---

## 9. Boas Praticas

- Sempre confirme descricao e valor antes de salvar.
- Em `Meio = Conta`, informe data correta do lancamento.
- Use o filtro de mes no Dashboard para analise por competencia.
- Em caso de duvida contabil, finalize liquidacao no sistema web.

---

## 10. FAQ e Solucao de Problemas

### 10.1 "Nao consigo entrar com biometria"

Verifique:

- biometria ativada no app;
- biometria habilitada no sistema operacional;
- existe sessao salva de login anterior.

### 10.2 "Entrei com dados errados e nao logou"

Comportamento esperado:

- app exibe mensagem de credenciais invalidas;
- permanece na tela de login para nova tentativa.

### 10.3 "Meus numeros parecem desatualizados"

Passos:

1. puxe para atualizar na tela;
2. confirme o mes selecionado no Dashboard;
3. valide se o dado esperado e aberto/vencido conforme regra da tela.

---

## Observacao Final

Este manual cobre o uso do app mobile no estado atual de producao.
Para operacoes de liquidacao, concilicao e rotinas contabilmente avancadas,
utilize o sistema web PRP Financeiro.
