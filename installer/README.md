# Instalador Simplificado (Windows/Linux)

Este diretório permite instalar o PRP Financeiro com Docker usando um comando (Linux) ou clique único (Windows).

## O que ele faz

- Cria `.env.prod` automaticamente a partir de `.env.prod.example` (se faltar).
- Define `PRP_ROOT_DIR=./runtime` para funcionar em Windows e Linux.
- Gera `SECRET_KEY` e `UPDATE_TOKEN` aleatórios se ainda estiverem com valor padrão.
- Sobe os 3 serviços de produção:
  - `prp-postgres-prod`
  - `prp-financeiro-prod`
  - `prp-updater-prod`

## Pré-requisito

- Docker + Docker Compose (`docker compose version` funcionando).

## Instalação Linux (comando único)

No diretório do projeto:

```bash
bash installer/linux/install.sh
```

## Instalação Windows (clique único)

- Execute `installer\windows\instalar_prp.bat`
- Ou no PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File installer\windows\install.ps1
```

## Acesso

- Aplicação web: `http://localhost:5000`

## Como gerar `.exe` (Windows - Inno Setup)

Script pronto:

- `installer\windows\PRPFinanceiroInstaller.iss`

### 1. Instalar Inno Setup

- Download: https://jrsoftware.org/isinfo.php

### 2. Compilar o instalador

Pelo prompt:

```powershell
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" "installer\windows\PRPFinanceiroInstaller.iss"
```

Ou com script pronto:

```powershell
powershell -ExecutionPolicy Bypass -File installer\windows\build_installer.ps1
```

### 3. Resultado

- O arquivo `PRPFinanceiro-Setup.exe` sera gerado em `installer\windows\`.
- Ao executar, ele instala os arquivos base e oferece executar `instalar_prp.bat` no final.
- Durante o setup, ha uma tela para informar `IP/dominio` do cliente.
  - O valor e salvo em `APP_PUBLIC_HOST` no `.env.prod`.
  - O instalador define `APP_BIND_IP` automaticamente:
    - `localhost`/`127.x.x.x` -> `127.0.0.1`
    - IP informado (ex.: `192.168.1.10`) -> mesmo IP
    - dominio (ex.: `erp.cliente.com.br`) -> `0.0.0.0`
