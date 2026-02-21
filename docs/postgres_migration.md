# Migracao para Postgres (HML)

Este guia considera o sistema em modo PostgreSQL-only.

## 1) Subir infraestrutura

No arquivo `.env`, configure:

```
POSTGRES_DB_HML=prp_financeiro
POSTGRES_USER_HML=prp_user
POSTGRES_PASSWORD_HML=zH23LJGicTj9SR
DATABASE_URL_HML=postgresql://prp_user:zH23LJGicTj9SR@prp-postgres-hml:5432/prp_financeiro
```

Suba os servicos:

```bash
docker compose -f docker-compose.hml.yml up -d --build
```

## 2) Garantir schema no Postgres

Ao iniciar o app com `DATABASE_URL_HML`, o app executa `db.create_all()` e cria as tabelas no Postgres.

## 3) Migrar dados do SQLite para Postgres

Execute no host:

```bash
python scripts/migrate_sqlite_to_postgres.py \
  --sqlite-path data/hml/prp_financeiro.db \
  --postgres-url "postgresql://prp_user:troque_esta_senha@localhost:5433/prp_financeiro" \
  --truncate-target
```

## 4) Validar

1. Acesse `http://127.0.0.1:5001/health`
2. Verifique login e dados principais (usuarios, entidades, titulos, ativos).
3. Faça backup antes do primeiro deploy com Postgres.

## 5) Rollback rapido (entre backups Postgres)

Use backup `.dump` e restore pelo endpoint de backup do sistema.
