# Guia Técnico: Sistema de Atualização Robusto (Enterprise Ready)

O PRP Financeiro agora utiliza um sistema de atualização nível enterprise, garantindo alta disponibilidade e segurança durante o processo de update.

## Arquitetura de Update

O processo envolve três componentes principais:
1. **App Flask (Backend)**: Gerencia o estado no banco de dados, expõe o status e aciona o Sidecar.
2. **Updater (Sidecar)**: Script isolado em container responsável por operações Docker, Healthchecks e Rollbacks.
3. **Frontend (Dashboard)**: Notifica o usuário e monitora a conclusão via polling de status.

## Fluxo de Operação

1. **Início**: O usuário admin clica em "Atualizar Agora". O Backend registra o início no DB e chama o Sidecar.
2. **Manutenção**: O app entra em `MAINTENANCE_MODE`, bloqueando rotas normais mas permitindo status e emergência.
3. **Deployment**:
   - O Sidecar faz pull da nova imagem.
   - Remove o container antigo (`rm -sf`) para evitar locks.
   - Sobe o novo com `--force-recreate`.
4. **Healthcheck**: 
   - O Sidecar aguarda e verifica `http://app:5000/health`.
   - Considera sucesso se retornar 200 (OK) ou 503 (Manutenção).
5. **Rollback**: Se o Healthcheck falhar após 15 tentativas (150s), o Sidecar restaura a tag anterior no `.env` e sobe a versão estável.
6. **Limpeza**: Após sucesso, o sistema remove imagens GHCR antigas, mantendo as últimas 3.

## Configuração de Ambiente

Crie ou edite os arquivos `.env.hml` e `.env.prod` na raiz do projeto:

```bash
# Exemplo .env.hml
ENVIRONMENT=hml
PRP_IMAGE_HML=ghcr.io/ademirapsantos/prp_financeiro:tag
COMPOSE_PROJECT_NAME=prp_financeiro_hml
KEEP_IMAGES=3
```

## Recuperação de Emergência

Caso o sistema trave em manutenção, você pode usar o comando de emergência via terminal ou API:

**Via API (Token necessário no Header):**
`POST /api/system/maintenance/off-token`

**Via Sidecar (Logs):**
Os logs detalhados ficam em `data/update_logs.jsonl`.
