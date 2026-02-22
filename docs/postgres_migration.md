# Operacao em PostgreSQL (HML/DEV)

Este projeto opera em modo PostgreSQL-only.

## 1) Variaveis de ambiente

Defina no `.env`:

```bash
POSTGRES_DB_HML=prp_financeiro
POSTGRES_USER_HML=prp_user
POSTGRES_PASSWORD_HML=CHANGE_ME
DATABASE_URL_HML=postgresql://prp_user:CHANGE_ME@prp-postgres-hml:5432/prp_financeiro
```

Para DEV:

```bash
DATABASE_URL_DEV=postgresql://prp_user:CHANGE_ME@localhost:5435/prp_financeiro
```

## 2) Subir stack

```bash
docker compose -f docker-compose.hml.yml up -d
```

## 3) Garantir schema

No startup, o app executa `db.create_all()` e migrações defensivas.

## 4) Validar

1. `curl http://127.0.0.1:5001/health`
2. Testar login e telas principais.
3. Gerar backup antes de qualquer mudança estrutural.
