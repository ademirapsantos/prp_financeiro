# Regras de Negócio Oficiais - PRP Financeiro

## Índice

1. [Conceito Contábil Adotado](#1-conceito-contabil-adotado)
2. [Definições Oficiais](#2-definicoes-oficiais)
3. [Regras de Títulos](#3-regras-de-titulos)
4. [Regras Contábeis](#4-regras-contabeis)
5. [Plano de Contas - Diretrizes Oficiais](#5-plano-de-contas---diretrizes-oficiais)
6. [Regras de Integridade](#6-regras-de-integridade)

## 1. Conceito Contábil Adotado {#1-conceito-contabil-adotado}

### 1.1 Regime operacional aplicado

O sistema aplica modelo híbrido operacional com predominância de competência para registro de obrigações e direitos por meio de títulos, e reconhecimento da efetiva movimentação financeira na etapa de liquidação.

Formalmente:

- criação de título representa constituição de direito (a receber) ou obrigação (a pagar), em status aberto;
- liquidação representa baixa financeira e atualização de status para pago;
- estorno representa reversão dos efeitos financeiros/contábeis conforme regras temporais implementadas.

### 1.2 Estrutura patrimonial

A estrutura patrimonial é suportada por plano de contas com tipos e naturezas, incluindo ativo, passivo, patrimônio líquido, receita e despesa, com utilização obrigatória de contas analíticas para lançamentos operacionais.

### 1.3 Natureza das contas

As contas contábeis possuem natureza (devedora/credora) e tipo contábil. O sistema valida compatibilidade de lançamentos em regras críticas, impedindo operações que contrariem natureza em contextos de receita/despesa.

### 1.4 Classificação contábil

A classificação é determinada por:

- código da conta;
- tipo da conta;
- natureza da conta;
- hierarquia (conta pai/filha) com distinção entre sintética e analítica.

## 2. Definições Oficiais {#2-definicoes-oficiais}

### 2.1 Título

Registro financeiro representativo de obrigação ou direito, associado a entidade, com valor, descrição, vencimento, tipo e status. É identificado por UUID próprio.

### 2.2 Receita

Evento classificado como entrada econômica vinculada a operações de receber, usualmente originando título do tipo `Receber` e posterior liquidação financeira.

### 2.3 Despesa

Evento classificado como saída econômica vinculada a operações de pagar, usualmente originando título do tipo `Pagar` e posterior liquidação financeira.

### 2.4 Ativo

Elemento patrimonial controlado pelo sistema, incluindo bancos/caixa e ativos não circulantes/investimentos, passível de compra, venda e recompra conforme tipo.

### 2.5 Passivo

Obrigações financeiras/contábeis reconhecidas no plano de contas e refletidas nas operações de títulos e demais eventos correlatos.

### 2.6 Patrimônio Líquido

Componente patrimonial utilizado em classificações e movimentações específicas de contrapartida, conforme parametrização e rotinas disponíveis.

### 2.7 Liquidação

Ato formal de baixa de título aberto, com atualização de status para pago, gravação de data de liquidação, criação de transação financeira e lançamentos contábeis correspondentes.

### 2.8 Competência

Referência temporal de reconhecimento de eventos financeiros/contábeis em módulos e relatórios que dependem de período de apuração.

### 2.9 Vencimento

Data limite originalmente atribuída ao título para exigibilidade/recebibilidade operacional.

## 3. Regras de Títulos {#3-regras-de-titulos}

### 3.1 Estados possíveis

Estados implementados para título:

- `Aberto`;
- `Pago`;
- `Cancelado`.

### 3.2 Transições permitidas

- criação: inexistente -> `Aberto`.
- liquidação: `Aberto` -> `Pago`.
- estorno (quando permitido): `Aberto` ou `Pago` -> `Cancelado`, com regras e efeitos específicos.

### 3.3 Transições proibidas

- cópia de título não pago.
- liquidação sem validações mínimas de conta/dados.
- estorno fora das janelas temporais implementadas.

### 3.4 Alterações permitidas antes da liquidação

No estado atual do sistema, não há rotina dedicada de edição direta do registro de título por tela/rota específica. Alterações operacionais são conduzidas por fluxos existentes (novo registro, liquidação, estorno, cópia quando aplicável).

### 3.5 Bloqueios após liquidação

Após liquidação, o comportamento muda por regras de segurança:

- título pago pode ser copiado (não editado diretamente por rota específica);
- estorno de título pago é bloqueado após 20 dias da data de liquidação;
- estorno geral é bloqueado para títulos com emissão superior a 60 dias.

### 3.6 Regras oficiais da funcionalidade “Copiar Título”

#### 3.6.1 Elegibilidade

A ação de cópia é elegível exclusivamente para título com status `Pago`.

#### 3.6.2 Exposição na interface

Na listagem de títulos, a ação `Copiar` é apresentada somente quando o status do item atende à condição de pago.

#### 3.6.3 Validação de acesso por rota

A rota de cópia valida:

- existência do título;
- status pago.

Em caso de descumprimento, o sistema bloqueia a operação com mensagem amigável e redirecionamento.

#### 3.6.4 Escopo de dados copiados

Os campos efetivamente levados como defaults para novo lançamento são:

- entidade (`entidade_id`);
- descrição (`descricao`);
- valor (`valor`);
- data de vencimento (`data_vencimento`);
- identificador de origem para contexto de interface (`copied_from_id`).

#### 3.6.5 Persistência

A operação de cópia não persiste novo registro no ato do clique. O sistema apenas redireciona para formulário de criação (`venda` ou `pagamento`) com dados pré-preenchidos.

#### 3.6.6 Constituição do novo registro

Ao salvar o formulário pré-preenchido:

- um novo título é criado com novo UUID;
- o título original permanece intacto;
- o novo título segue fluxo padrão de criação, iniciando em estado aberto.

#### 3.6.7 Efeito sobre liquidação da origem

É vedada qualquer duplicação de baixa, transação financeira de liquidação ou partidas contábeis já associadas ao título original pago.

## 4. Regras Contábeis {#4-regras-contabeis}

### 4.1 Registro de receitas

Receitas são registradas por títulos a receber e demais rotinas correlatas, com reflexos contábeis conforme serviços internos e contas parametrizadas.

### 4.2 Registro de despesas

Despesas são registradas por títulos a pagar e operações correlatas (inclusive cartão/ativos quando aplicável), com reflexos contábeis conforme regras do serviço.

### 4.3 Tratamento de liquidação

Liquidação implica simultaneamente:

- mudança de estado do título;
- evento financeiro em conta de ativo (banco/caixa);
- evento contábil no diário por partidas dobradas.

### 4.4 Impacto patrimonial

Há impacto patrimonial quando eventos afetam contas patrimoniais (ativo, passivo, patrimônio líquido), incluindo baixa em bancos/caixa e operações de ativos.

### 4.5 Impacto em resultado

Há impacto em resultado quando a operação envolve contas de receita/despesa, observado o encadeamento da regra implementada e os parâmetros contábeis aplicáveis.

### 4.6 Vinculação ao plano de contas

Toda escrituração depende de contas válidas e analíticas. O sistema aplica validações para evitar lançamentos em contas sintéticas e para preservar coerência de natureza.

## 5. Plano de Contas - Diretrizes Oficiais {#5-plano-de-contas---diretrizes-oficiais}

### 5.1 Estrutura recomendada

- codificação hierárquica coerente;
- separação por tipo (ativo, passivo, PL, receita, despesa);
- uso de conta pai para agregação e conta analítica para lançamento.

### 5.2 Criação de conta coerente

Conta deve ser cadastrada com:

- código único;
- nome representativo;
- tipo correto;
- natureza consistente;
- conta pai quando aplicável.

### 5.3 Natureza devedora/credora

A natureza deve ser compatível com o comportamento contábil esperado da conta. Regras de serviço bloqueiam combinações indevidas em cenários críticos (ex.: receita debitada e despesa creditada quando incompatível).

### 5.4 Exemplos corretos

- conta analítica de despesa operacional vinculada a fornecedor;
- conta analítica de receita operacional vinculada a cliente;
- conta de banco/caixa no ativo para liquidação.

### 5.5 Exemplos incorretos

- lançar evento operacional em conta sintética;
- usar conta de natureza incompatível com tipo de lançamento;
- duplicar código contábil já existente.

### 5.6 Erros comuns

- parametrização incompleta de entidades;
- seleção de conta inadequada para baixa/liquidação;
- tentativa de estorno fora das regras de prazo.

### 5.7 Boas práticas contábeis no sistema

- padronizar cadastro e nomenclatura de contas;
- revisar periodicamente balancete e diário;
- manter parâmetros contábeis globais atualizados;
- utilizar estorno de forma controlada e dentro dos limites implementados.

## 6. Regras de Integridade {#6-regras-de-integridade}

### 6.1 Fundamentação do bloqueio de exclusões/estornos

O bloqueio por janelas temporais protege consistência contábil e reduz risco de reabertura indevida de períodos já operacionalmente consolidados.

### 6.2 Fundamentação da alteração de comportamento após liquidação

Uma vez liquidado, o título deixa de representar pendência e passa a ter trilha de baixa financeira e contábil associada. Qualquer reversão precisa observar controles específicos de prazo e serviço.

### 6.3 Fundamentação da cópia restrita a título pago

A cópia foi implementada como mecanismo de reaproveitamento de dados de eventos já concluídos, preservando previsibilidade operacional e evitando confusão com títulos ainda em aberto/cancelados.

### 6.4 Justificativa contábil das restrições

As restrições implementadas têm objetivo de:

- preservar rastreabilidade;
- impedir duplicidade de efeito financeiro;
- impedir reprocessamento indevido de baixa;
- manter coerência entre situação do título e estado contábil registrado.

### 6.5 Integridade transacional

Fluxos críticos adotam padrão:

- validação prévia;
- execução da regra de negócio;
- `commit` em sucesso;
- `rollback` em exceção.

Esse comportamento previne persistência parcial em operações financeiras e contábeis.

### 6.6 Integridade de atualização de versão

A estratégia de updater com lock, backup, health check e rollback automático reforça a continuidade operacional e a proteção dos dados em ciclos de atualização.
