# PRP Financeiro

Sistema web em Python/Flask para controle financeiro com contabilidade automatica, operando em Docker com PostgreSQL e processo de atualizacao automatica por ambiente.

Versao atual: `1.4.13` (`app/version.py`)

## 1. Visao Geral

O projeto cobre:
- autenticacao de usuarios (admin e usuario comum)
- dashboard financeiro com indicadores
- contas a pagar/receber (titulos)
- bancos/ativos
- cartao de credito (faturas, pagamentos, encargos)
- modulo contabil (plano de contas, diario, balancete)
- notificacoes do sistema
- atualizacao de versao com sidecar updater, healthcheck e rollback automatico

## 2. Stack Tecnica

- Python 3 + Flask
- SQLAlchemy (`Flask-SQLAlchemy`)
- PostgreSQL 16
- Driver PostgreSQL: `psycopg` (`psycopg[binary]==3.2.13`)
- Gunicorn
- Docker Compose

## 3. Arquitetura de Containers

Cada ambiente possui 3 servicos principais:

1. App (`prp-financeiro-*`)
2. Banco PostgreSQL (`prp-postgres-*`)
3. Updater Sidecar (`prp-updater-*`)

Arquivos:
- `docker-compose.yml` (dev/test)
- `docker-compose.hml.yml` (homologacao)
- `docker-compose.prod.yml` (producao)

## 4. Banco de Dados

O sistema esta em modo PostgreSQL.

Resolucao da conexao:
- `DATABASE_URL`
- fallback por ambiente: `DATABASE_URL_DEV`, `DATABASE_URL_HML`, `DATABASE_URL_PROD`

Implementacao: `app/config.py`.

Observacoes importantes:
- sem `DATABASE_URL`, a aplicacao falha na subida (comportamento esperado)
- IDs dos modelos estao em UUID string (`String(36)`)

## 5. Como Rodar Local (Dev/Test)

## 5.1 Subir stack

```powershell
docker compose up -d
docker compose ps
```

App local (dev/test):
- `http://localhost:5002`

Banco local (dev/test):
- host `localhost`, porta `5435`

## 5.2 Logs

```powershell
docker compose logs -f --tail=200 prp-financeiro-test
docker compose logs -f --tail=200 prp-updater
```

## 6. Homologacao (HML)

## 6.1 Subir

```powershell
docker compose -f docker-compose.hml.yml up -d
docker compose -f docker-compose.hml.yml ps
```

App HML:
- `http://localhost:5001`

Updater HML:
- `http://localhost:5015`

Banco HML:
- host `localhost`, porta `5433`

## 6.2 Recriar somente app HML

```powershell
docker compose -f docker-compose.hml.yml up -d --force-recreate prp-financeiro-hml
```

## 7. Variaveis de Ambiente Relevantes

Exemplos mais usados:

- `DATABASE_URL_HML=postgresql://prp_user:<senha>@prp-postgres-hml:5432/prp_financeiro`
- `DATABASE_URL_PROD=postgresql://prp_user:<senha>@prp-postgres-prod:5432/prp_financeiro`
- `UPDATE_TOKEN=<token>`
- `ENVIRONMENT=hml|prod|dev`
- `MANIFEST_BASE_URL=https://ademirapsantos.github.io/prp_financeiro`
- `PRP_IMAGE_HML=ghcr.io/ademirapsantos/prp_financeiro:hml-vX.Y.Z`
- `PRP_IMAGE_PROD=ghcr.io/ademirapsantos/prp_financeiro:prod-vX.Y.Z`

## 8. Atualizacao de Versao (Workflow de Deploy)

Fluxo resumido:

1. App detecta nova versao via manifesto (`/api/system/latest`)
2. Usuario admin confirma atualizacao
3. App ativa modo manutencao (`MAINTENANCE_MODE=true`, `UPDATE_IN_PROGRESS=true`)
4. App chama sidecar updater (`/api/update`)
5. Updater:
   - cria backup logico com `pg_dump` (se `DATABASE_URL` estiver disponivel)
   - troca tag da imagem no `.env` do ambiente
   - executa `docker compose pull` + `up --force-recreate`
   - valida `/health`
   - se falhar, executa rollback para tag anterior
6. Updater finaliza estado no app (`/api/system/update/finalize-token`)
7. Frontend de manutencao faz polling em `/api/system/update/status` e redireciona quando normalizar

Arquivos principais:
- `app/routes.py`
- `updater.py`
- `app/templates/manutencao.html`

## 9. Gunicorn / Timeout

Configuracao atual com timeout estendido para evitar abortos prematuros:
- `--timeout 120`
- `--graceful-timeout 120`
- `--keep-alive 5`

Aplicado em:
- `Dockerfile`
- `docker-compose.yml`
- `docker-compose.hml.yml`
- `docker-compose.prod.yml`

## 10. Endpoints de Operacao

Saude e versao:
- `GET /health`
- `GET /api/version`
- `GET /api/system/latest`
- `GET /api/system/update/status`

Controle de update/manutencao:
- `POST /api/system/update/start` (admin logado)
- `POST /api/system/update/finalize-token` (sidecar, com token)
- `POST /api/system/maintenance/off-token` (emergencia, com token)

## 11. Problemas Comuns e Solucao

## 11.1 `ModuleNotFoundError: No module named 'psycopg2'`

Causa comum:
- imagem antiga sendo usada (sem driver novo)

Acao:
1. confirmar tag em uso (`PRP_IMAGE_HML`/`PRP_IMAGE_PROD`)
2. publicar imagem nova com `psycopg[binary]`
3. `docker compose pull` + `up -d --force-recreate`

## 11.2 Erro 500 ao iniciar

Verificar:
- `DATABASE_URL` correto
- banco acessivel na rede Docker
- logs do container app

## 11.3 `curl` no PowerShell pedindo `Uri`

No PowerShell, prefira:

```powershell
curl.exe -i http://localhost:5001/health
```

ou:

```powershell
Invoke-WebRequest -Uri http://localhost:5001/health
```

## 11.4 Pull/deploy parece travado

Checar em paralelo:
- logs do app
- logs do updater
- status dos containers
- arquivo de lock do updater

Comandos:

```powershell
docker compose -f docker-compose.hml.yml ps
docker compose -f docker-compose.hml.yml logs --tail=200 prp-financeiro-hml
docker compose -f docker-compose.hml.yml logs --tail=200 prp-updater-hml
```

## 12. Backup e Restore

Backup (manual, exemplo HML):

```powershell
docker exec prp-postgres-hml pg_dump -U prp_user -d prp_financeiro -Fc -f /tmp/hml.dump
docker cp prp-postgres-hml:/tmp/hml.dump .\hml.dump
```

Restore (manual, exemplo HML):

```powershell
docker cp .\hml.dump prp-postgres-hml:/tmp/hml.dump
docker exec prp-postgres-hml pg_restore -U prp_user -d prp_financeiro --clean --if-exists /tmp/hml.dump
```

## 13. Estrutura de Pastas (resumo)

- `app/` codigo Flask (rotas, modelos, templates)
- `manifests/` manifesto de versoes por ambiente
- `migrations/` migracoes Alembic
- `data/` dados persistidos por ambiente
- `docs/` documentacao adicional
- `updater.py` servico sidecar de update

## 14. Seguranca e Boas Praticas

- nao commitar tokens/senhas reais
- usar `.env` por ambiente
- validar backup antes de mudancas estruturais
- aplicar mudancas de schema com migracoes versionadas (Alembic)

## 15. Documentacao Complementar

- Guia de update: `UPDATE_GUIDE.md`
- Manual funcional: `MANUAL_USUARIO.md`

