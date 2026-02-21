# Guia do Sistema de Atualização PRP Financeiro

Este documento descreve o funcionamento do sistema de atualização profissional (Enterprise Grade) implementado no projeto.

## Arquitetura
O sistema é composto por:
1.  **Frontend (App)**: Detecta atualizações via manifest remoto e exibe notificações.
2.  **Backend (App)**: Gerencia sinalizações de manutenção e solicita a atualização ao Updater.
3.  **Updater Service**: Um container isolado que gerencia Docker Compose, Pull de imagens, Healthchecks e Rollbacks.

## Fluxo de Atualização Silenciosa e Segura
Quando uma atualização é iniciada:
1.  O app entra em **Modo Manutenção**.
2.  O Updater baixa a nova imagem baseada na tag do manifest (`hml.json` ou `prod.json`).
3.  O Updater atualiza o arquivo `.env` do projeto com a nova tag da imagem.
4.  O serviço é recriado (`docker compose up -d`).
5.  **Health Check**: O Updater monitora o status do container por até 200 segundos.
    - Se o container responder `healthy` no endpoint `/health`, a atualização é concluída.
    - Se o container ficar `unhealthy` ou falhar ao subir, o **Rollback Automático** é acionado.

## Rollback Automático
Se a nova versão estiver quebrada (erro de código, falha de conexão com banco, etc.):
1.  O Updater detecta a falha de saúde (Health Check).
2.  Ele restaura a tag da imagem anterior no arquivo `.env`.
3.  O serviço é reiniciado com a versão estável anterior.
4.  Um log de erro é registrado em `data/update_logs.jsonl`.

## Logs e Monitoramento
Os logs de todas as tentativas de atualização são salvos em formato JSONL em:
`prp_financeiro/data/update_logs.jsonl`

Exemplo de entrada de log:
```json
{"timestamp": "2026-02-20T22:00:00", "event": "update_start", "details": {"update_id": "uuid...", "env": "hml"}}
{"timestamp": "2026-02-20T22:01:30", "event": "health_failed", "details": {"action": "auto_rollback"}}
```

## Pipeline de CI/CD (GitHub Actions)
A aplicação utiliza uma estrutura de automação simplificada e consistente:

### Workflows Oficiais
1.  **Build and Push (GHCR)** (`publish-ghcr.yml`):
    - Gatilho: Push nas branches `release` (HML) ou `main` (PROD).
    - Função: Constrói a imagem Docker (com Buildx e Cache) e publica no GitHub Container Registry.
    - Tags: `hml-latest`/`hml-vX.Y.Z` ou `prod-latest`/`prod-vX.Y.Z`.
2.  **Publish Manifest** (`publish-manifest-hml.yml` / `publish-manifest-prod.yml`):
    - Gatilho: Sucesso do push nas branches respectivas.
    - Função: Gera o `hml.json` ou `prod.json` e publica no GitHub Pages.
    - URLs:
      - `https://ademirapsantos.github.io/prp_financeiro/hml.json`
      - `https://ademirapsantos.github.io/prp_financeiro/prod.json`
3.  **Validate Merge Logic** (`validate-merge.yml`):
    - Gatilho: PR para `main` ou `release`.
    - Regras: `main` só aceita PR de `release`. `release` só aceita PR de `dev`.
4.  **Docker Build Check** (`docker-build.yml`):
    - Gatilho: PR para `release` ou `dev`.
    - Função: Valida se a imagem constrói corretamente sem publicar.

### Formato do Manifest
Os arquivos JSON de manifest seguem este padrão para compatibilidade com o updater:
```json
{
  "version": "1.4.2",
  "latest_version": "1.4.2",
  "tag": "hml-v1.4.2",
  "commit": "<sha-do-commit>",
  "date": "<data-iso-utc>",
  "environment": "hml"
}
```
