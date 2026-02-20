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

## Configuração de Ambiente (Variáveis)
- `UPDATER_BASE_URL`: URL do serviço updater.
- `UPDATE_TOKEN`: Token de segurança para comunicação inter-service.
- `MANIFEST_BASE_URL`: URL base onde os arquivos `.json` de versão estão hospedados.
- `ENVIRONMENT`: `hml` ou `prod`.
- `GHCR_IMAGE`: Nome base da imagem no GitHub Container Registry.
