# Manual Técnico - PRP Financeiro

## Índice

1. [Arquitetura Geral](#1-arquitetura-geral)
2. [Regras Técnicas Críticas](#2-regras-tecnicas-criticas)
3. [Fluxos Técnicos](#3-fluxos-tecnicos)
4. [Banco de Dados](#4-banco-de-dados)
5. [Estratégia de Update Seguro](#5-estrategia-de-update-seguro)

## 1. Arquitetura Geral {#1-arquitetura-geral}

### 1.1 Stack utilizada

- Linguagem: Python 3.11 (containers principais).
- Framework web: Flask.
- ORM: SQLAlchemy (`flask_sqlalchemy`).
- Banco de dados: PostgreSQL.
- Frontend server-side: Jinja2 templates.
- Autenticação de sessão: Flask-Login.
- Empacotamento/runtime: Docker e Docker Compose.
- Atualização remota: serviço `updater` dedicado.
- CI/CD: GitHub Actions.

### 1.2 Estrutura de pastas (visão funcional)

- `app/`
- `app/__init__.py`: bootstrap da aplicação, blueprints, hooks globais, contexto.
- `app/models.py`: entidades ORM, enums, relacionamentos e constraints.
- `app/services.py`: regras de negócio e contabilidade (financeiro, ativos, cartões).
- `app/routes*.py`: camadas HTTP por domínio funcional.
- `app/templates/`: telas e formulários.
- `app/static/`: assets estáticos.
- `updater.py`: serviço de atualização/rollback.
- `docker-compose*.yml`: orquestração por ambiente.
- `.github/workflows/`: pipelines de build/publicação/deploy.

### 1.3 Separação de responsabilidades

- Rotas (`routes_*.py`): validação de entrada HTTP, navegação, flash messages.
- Serviços (`services.py`): regra transacional e consistência contábil.
- Modelos (`models.py`): estrutura de dados, enums e integridade relacional.
- Templates: interface e condicionais de exibição (ex.: botão `Copiar` por status).

### 1.4 Docker (app, banco, updater)

Arquitetura padrão por compose:

- `app`: container Flask (porta interna 5000).
- `db`: PostgreSQL com volume persistente.
- `updater`: API auxiliar (porta 8000 interna) para operações de atualização.

Observações por ambiente:

- DEV/HMG podem ser operados localmente com compose dedicado.
- PRD possui compose próprio com volumes persistentes e updater habilitado.

### 1.5 Pipeline CI/CD

Workflows identificados:

- `docker-build.yml`: valida build de imagem e consistência de compose.
- `publish-ghcr.yml`: publica imagens no GHCR (tags por branch/release).
- `publish-manifest-dev.yml`, `publish-manifest-hml.yml`, `publish-manifest-prod.yml`: publica manifestos de versão por ambiente.
- `validate-merge.yml`: valida política de merge e branch source.
- `deploy-prod-hostinger.yml`, `rollback-prod-hostinger.yml`, `maintenance-prod-hostinger.yml`: operação manual de PRD na Hostinger.

## 2. Regras Técnicas Críticas {#2-regras-tecnicas-criticas}

### 2.1 Tratamento de UUID

- chaves primárias são majoritariamente `String(36)` com UUID em formato texto.
- novas entidades críticas (ex.: `Titulo`) recebem novo UUID no cadastro.
- cópia de título nunca reaproveita o ID original.

### 2.2 Tratamento de status

Enums centrais:

- `StatusTitulo`: `Aberto`, `Pago`, `Cancelado`.
- `TipoTitulo`: `Pagar`, `Receber`.

Regras de uso:

- criação inicia em `Aberto`;
- liquidação muda para `Pago`;
- estorno de título aplica cancelamento e reversões conforme fluxo.

### 2.3 Tratamento de liquidação

`FinancialService.liquidar_titulo` executa, no mesmo contexto transacional:

- valida estado e parâmetros;
- atualiza título (status/data);
- registra `TransacaoFinanceira`;
- ajusta saldo de banco/caixa;
- gera partidas contábeis (via `AccountingService`).

### 2.4 Proteção de integridade

Camadas de proteção identificadas:

- validações de rota (existência de entidade/título/banco);
- validações de serviço (estado, valores, natureza contábil);
- constraints de banco (unicidade em campos como código de conta);
- regra de partidas dobradas (`débito == crédito`) e contas analíticas obrigatórias;
- bloqueio de lançamentos contrários à natureza de receita/despesa.

### 2.5 Bloqueio de exclusão/estorno indevido

No fluxo de títulos:

- estorno de título pago bloqueado se liquidação for anterior a 20 dias.
- estorno geral bloqueado se emissão for anterior a 60 dias.

No fluxo de ativos/cartões:

- estornos e ajustes passam por serviços com validações próprias antes de `commit`.

### 2.6 Controle de ambiente (DEV/HMG/PRD)

- variável `ENVIRONMENT` controla sinalização de ambiente e seleção de configurações.
- `Config` busca `DATABASE_URL` com fallback para `DATABASE_URL_<ENV>`.
- compose e workflows segmentam comportamento de publicação/deploy por ambiente.

### 2.7 Variáveis de ambiente críticas

- `DATABASE_URL` / `DATABASE_URL_DEV` / `DATABASE_URL_HML` / `DATABASE_URL_PRD`.
- `SECRET_KEY`.
- variáveis do updater (token, manifest URL base, etc.).
- parâmetros SMTP (quando habilitados via interface/API administrativa).

## 3. Fluxos Técnicos {#3-fluxos-tecnicos}

### 3.1 Criação de título

Rotas:

- `GET/POST /financeiro/venda`.
- `GET/POST /financeiro/pagamento`.

Fluxo técnico:

1. rota recebe dados do formulário;
2. converte tipos (valor/data);
3. obtém entidade por ID;
4. chama `FinancialService.criar_titulo_receber` ou `criar_titulo_pagar`;
5. persiste com `commit`;
6. em falha: `rollback` + mensagem de erro.

### 3.2 Liquidação de título

Rotas:

- `GET/POST /financeiro/liquidar/<titulo_id>`.
- `POST /financeiro/api/liquidar/<titulo_id>`.

Fluxo técnico:

1. busca título;
2. valida entrada (banco/data/desconto);
3. chama `FinancialService.liquidar_titulo`;
4. serviço registra transação e partidas de baixa;
5. confirma transação (`commit`) ou desfaz (`rollback`).

### 3.3 Cópia de título

Rota:

- `GET /financeiro/titulos/<titulo_id>/copiar`.

Fluxo técnico:

1. resolve `next_url`.
2. busca título por ID.
3. valida existência.
4. valida status pago (`_titulo_esta_pago`).
5. monta defaults (`_build_titulo_copy_defaults`) com campos permitidos.
6. redireciona:
   - título `Receber` -> `/financeiro/venda` com query params;
   - título `Pagar` -> `/financeiro/pagamento` com query params.
7. formulário abre pré-preenchido; persistência só ocorre no `POST` de criação.

Garantias:

- não duplica liquidação nem transações financeiras do título original;
- novo título nasce com novo UUID e status inicial de aberto (pela rotina padrão de criação).

### 3.4 Geração de lançamentos contábeis

Origens principais:

- liquidação de títulos;
- movimentações financeiras (`movimentacao_outros`, transferências);
- operações de ativos (compra/venda/recompra);
- cartões (compras/faturas/estornos).

Regra central (`AccountingService`):

- somente contas analíticas;
- partidas balanceadas;
- validação de natureza por tipo da conta.

### 3.5 Atualizações automáticas

Componente: `updater.py`.

Sequência principal:

1. recebe requisição autenticada (`/api/update`);
2. aplica lock de atualização;
3. consulta manifesto por ambiente;
4. compara tag alvo com tag atual;
5. gera backup de banco (`pg_dump`) quando aplicável;
6. atualiza imagem/tag no compose do serviço alvo;
7. sobe container atualizado;
8. executa health check;
9. em falha: rollback automático de tag e restauração de backup quando necessário;
10. remove lock e registra conclusão.

## 4. Banco de Dados {#4-banco-de-dados}

### 4.1 Principais tabelas

Financeiro e contábil:

- `titulos`
- `transacoes_financeiras`
- `livro_diario`
- `partidas_diario`
- `contas_contabeis`
- `configuracoes`

Cadastros:

- `entidades`
- `ativos`

Cartão de crédito:

- `cartoes_credito`
- `transacoes_cartao`
- `faturas_cartao`

Administração e operação:

- `users`
- `smtp_configs`
- `notificacoes`
- `update_log`

### 4.2 Relacionamentos relevantes

- `Titulo` -> `Entidade` (N:1).
- `TransacaoFinanceira` -> `Titulo` e `Ativo` (banco/caixa).
- `PartidaDiario` -> `LivroDiario` e `ContaContabil`.
- `Ativo` -> `ContaContabil`.
- `CartaoCredito` -> `Ativo` (banco) e `ContaContabil`.
- `TransacaoCartao` -> `CartaoCredito` e `FaturaCartao`.

### 4.3 Regras de integridade

- códigos de conta contábil com unicidade lógica/constraint.
- consistência enum/status em fluxos de transição.
- bloqueios de estorno por janelas temporais.
- validações de serviço antes de qualquer `commit`.

### 4.4 Restrições importantes

- lançamentos contábeis em contas sintéticas são rejeitados;
- natureza de conta é verificada para operações de receita/despesa;
- cópia de título é permitida apenas para `Pago`.

## 5. Estratégia de Update Seguro {#5-estrategia-de-update-seguro}

### 5.1 Preservação de dados

- banco em volume persistente;
- backup pré-update via `pg_dump` quando necessário;
- rollback automático com retorno à tag anterior.

### 5.2 Migrations

- mecanismo de migração defensiva inicial no bootstrap (`run_defensive_migrations`);
- updater suporta execução de comando de migração quando sinalizado no manifesto.

### 5.3 Prevenção de perda de dados

- lock para impedir updates concorrentes;
- health checks pós-deploy;
- rollback automático por falha;
- finalização controlada via token entre app e updater.

### 5.4 Operação recomendada por ambiente

- DEV/HMG local: atualização controlada pelo operador local.
- PRD Hostinger: execução por workflow manual de deploy/rollback/maintenance e monitoramento de saúde da aplicação.
