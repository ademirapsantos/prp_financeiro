# Manual de Instalação - PRP Financeiro (Windows e Linux)

Este manual descreve como instalar o PRP Financeiro usando Docker, com processo simplificado para cliente final.

## 1. Pré-requisitos

- Máquina Windows 10/11 ou Linux (Ubuntu/Debian/CentOS)
- Docker instalado e em execução
- Docker Compose habilitado (`docker compose`)
- Acesso à internet para baixar imagens dos containers

## 2. O que será instalado

O ambiente sobe 3 containers:

- `prp-financeiro-prod` (aplicação web)
- `prp-updater-prod` (serviço de atualização)
- `prp-postgres-prod` (banco de dados PostgreSQL)

## 3. Estrutura de arquivos persistidos

Os dados ficam em `./runtime` dentro da pasta da aplicação:

- `runtime/postgres` (dados do banco)
- `runtime/data` (dados da aplicação)
- `runtime/manifests` (manifestos de atualização)

## 4. Instalação no Windows

### Opção A (recomendada para cliente final): instalador `.exe`

1. Execute `PRPFinanceiro-Setup.exe`.
2. Durante o setup, informe o `IP/domínio` de acesso quando solicitado.
3. No fim da instalação, execute `Instalar PRP Financeiro`.
4. Aguarde a criação e subida dos containers.
5. Acesse no navegador:
   - `http://localhost:5000` (instalação local)
   - ou `http://<ip-ou-dominio>:5000`

### Opção B (sem `.exe`, via script)

No PowerShell, dentro da pasta do projeto:

```powershell
powershell -ExecutionPolicy Bypass -File installer\windows\install.ps1
```

Ou com clique duplo:

- `installer\windows\instalar_prp.bat`

## 5. Instalação no Linux

No terminal, dentro da pasta do projeto:

```bash
bash installer/linux/install.sh
```

Após concluir:

- acessar `http://localhost:5000`

Se for acesso remoto na rede, ajuste `APP_BIND_IP` no `.env.prod` (ex.: `0.0.0.0` ou IP da máquina).

## 6. Verificação pós-instalação

Ver status dos containers:

```bash
docker compose --env-file .env.prod -f docker-compose.prod.yml -f docker-compose.prod.override.yml ps
```

Ver logs da aplicação:

```bash
docker compose --env-file .env.prod -f docker-compose.prod.yml -f docker-compose.prod.override.yml logs -f prp-financeiro-prod
```

## 7. Comandos úteis de operação

Subir ambiente:

```bash
docker compose --env-file .env.prod -f docker-compose.prod.yml -f docker-compose.prod.override.yml up -d
```

Parar ambiente:

```bash
docker compose --env-file .env.prod -f docker-compose.prod.yml -f docker-compose.prod.override.yml down
```

Reiniciar apenas a aplicação:

```bash
docker compose --env-file .env.prod -f docker-compose.prod.yml -f docker-compose.prod.override.yml restart prp-financeiro-prod
```

## 8. Arquivo de configuração principal (`.env.prod`)

Campos importantes:

- `APP_BIND_IP`:
  - `127.0.0.1` = acesso só local
  - `0.0.0.0` = acesso pela rede
  - `192.168.x.x` = bind em IP específico
- `APP_PUBLIC_HOST`: IP/domínio que o cliente usa para acessar
- `PRP_IMAGE_PROD` e `UPDATER_IMAGE_PROD`: tags das imagens
- `POSTGRES_*` e `DATABASE_URL_PROD`: credenciais e conexão do banco
- `SECRET_KEY` e `UPDATE_TOKEN`: segurança do sistema

## 9. Troubleshooting rápido

- Docker não inicia:
  - abrir Docker Desktop (Windows) ou serviço Docker (Linux)
- Porta 5000 em uso:
  - ajustar porta no `docker-compose.prod.yml` e reiniciar
- Não acessa de outra máquina:
  - conferir `APP_BIND_IP`
  - liberar firewall (porta 5000)
- Erro de pull de imagem:
  - validar internet/proxy e nome da imagem/tag no `.env.prod`

## 10. Desinstalação

Parar e remover containers:

```bash
docker compose --env-file .env.prod -f docker-compose.prod.yml -f docker-compose.prod.override.yml down
```

Remover dados persistidos (opcional, irreversível):

- apagar a pasta `runtime/`

