# PRP Financeiro - Guia de Producao (VPS 1GB)

Este guia cobre o deploy de producao com Docker Compose em VPS pequena (Oracle VM.Standard.E2.1.Micro: 1 OCPU / 1GB RAM), com foco em estabilidade, seguranca e previsibilidade.

## 1. Preparar VPS

### 1.1 Ativar swap (recomendado para reduzir risco de OOM)

```bash
sudo fallocate -l 1G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
free -h
```

### 1.2 Instalar Docker + Compose plugin

```bash
sudo apt-get update
sudo apt-get install -y docker.io docker-compose-plugin
sudo systemctl enable --now docker
sudo usermod -aG docker $USER
```

Abra nova sessao SSH apos adicionar usuario ao grupo `docker`.

## 2. Estrutura de diretorios na VPS

```bash
sudo mkdir -p /srv/prp_financeiro/{postgres,data,backup}
sudo chown -R $USER:$USER /srv/prp_financeiro
```

## 3. Arquivo de ambiente de producao

No servidor, dentro da pasta do projeto:

```bash
cp .env.prod.example /srv/prp_financeiro/.env.prod
```

Edite `/srv/prp_financeiro/.env.prod` com valores reais e fortes (nao commitar).

## 4. Deploy de producao

Executar sempre com `--env-file` e os dois arquivos Compose:

```bash
docker compose \
  --env-file /srv/prp_financeiro/.env.prod \
  -f docker-compose.prod.yml \
  -f docker-compose.prod.override.yml \
  up -d
```

## 5. Operacao basica

### 5.1 Status

```bash
docker compose \
  --env-file /srv/prp_financeiro/.env.prod \
  -f docker-compose.prod.yml \
  -f docker-compose.prod.override.yml \
  ps
```

### 5.2 Logs

```bash
docker compose \
  --env-file /srv/prp_financeiro/.env.prod \
  -f docker-compose.prod.yml \
  -f docker-compose.prod.override.yml \
  logs -f --tail=200 prp-financeiro-prod
```

```bash
docker compose \
  --env-file /srv/prp_financeiro/.env.prod \
  -f docker-compose.prod.yml \
  -f docker-compose.prod.override.yml \
  logs -f --tail=200 prp-updater-prod
```

### 5.3 Healthcheck da aplicacao

```bash
curl http://localhost:5000/health
```

## 6. Backup PostgreSQL

Gerar dump em `/srv/prp_financeiro/backup/`:

```bash
docker exec prp-postgres-prod \
  pg_dump -U "$POSTGRES_USER_PROD" -d "$POSTGRES_DB_PROD" -Fc \
  > /srv/prp_financeiro/backup/prp_financeiro_$(date +%F_%H%M).dump
```

## 7. Acesso ao PostgreSQL sem expor porta

O Postgres de producao nao deve publicar porta no host.
Quando precisar acessar localmente, use tunel SSH:

```bash
ssh -L 55432:127.0.0.1:5432 <usuario>@<ip-da-vps>
```

No servidor, conecte no container pelo socket interno:

```bash
docker exec -it prp-postgres-prod psql -U "$POSTGRES_USER_PROD" -d "$POSTGRES_DB_PROD"
```

Se precisar acessar com cliente local (via tunel), rode um proxy local na VPS somente durante a manutencao (evitar permanente).

