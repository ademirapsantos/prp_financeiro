#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
ENV_FILE="${PROJECT_ROOT}/.env.prod"
ENV_EXAMPLE="${PROJECT_ROOT}/.env.prod.example"
RUNTIME_DIR="${PROJECT_ROOT}/runtime"

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Erro: comando '$1' nao encontrado."
    exit 1
  fi
}

random_hex() {
  if command -v openssl >/dev/null 2>&1; then
    openssl rand -hex 32
  else
    head -c 32 /dev/urandom | od -An -tx1 | tr -d ' \n'
  fi
}

upsert_env() {
  local key="$1"
  local value="$2"
  if grep -qE "^${key}=" "$ENV_FILE"; then
    sed -i "s|^${key}=.*|${key}=${value}|g" "$ENV_FILE"
  else
    printf "\n%s=%s\n" "$key" "$value" >>"$ENV_FILE"
  fi
}

echo "==> Validando prerequisitos..."
require_cmd docker
docker compose version >/dev/null

if [[ ! -f "$ENV_FILE" ]]; then
  if [[ ! -f "$ENV_EXAMPLE" ]]; then
    echo "Erro: .env.prod e .env.prod.example nao encontrados."
    exit 1
  fi
  cp "$ENV_EXAMPLE" "$ENV_FILE"
  echo "==> Arquivo .env.prod criado a partir do exemplo."
fi

echo "==> Preparando variaveis de ambiente..."
upsert_env "PRP_ROOT_DIR" "./runtime"

if grep -qE '^SECRET_KEY=(|prod_key_change_me)$' "$ENV_FILE"; then
  upsert_env "SECRET_KEY" "$(random_hex)"
fi

if grep -qE '^UPDATE_TOKEN=(|prp_secure_token_2026)$' "$ENV_FILE"; then
  upsert_env "UPDATE_TOKEN" "$(random_hex)"
fi

echo "==> Criando diretorios locais..."
mkdir -p "${RUNTIME_DIR}/postgres" "${RUNTIME_DIR}/data" "${RUNTIME_DIR}/manifests"

echo "==> Baixando imagens..."
docker compose \
  --env-file "$ENV_FILE" \
  -f "${PROJECT_ROOT}/docker-compose.prod.yml" \
  -f "${PROJECT_ROOT}/docker-compose.prod.override.yml" \
  pull

echo "==> Subindo servicos..."
docker compose \
  --env-file "$ENV_FILE" \
  -f "${PROJECT_ROOT}/docker-compose.prod.yml" \
  -f "${PROJECT_ROOT}/docker-compose.prod.override.yml" \
  up -d

echo "==> Instalacao finalizada."
echo "Aplicacao: http://localhost:5000"

