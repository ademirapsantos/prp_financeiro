# Sistema de CI/CD e Atualização Multi-Ambiente

O PRP Financeiro agora possui um pipeline de CI/CD completo e suporte a múltiplos ambientes.

## Estrutura de Ambientes
- **DEV**: Ambiente local de desenvolvimento. Sem auto-deploy.
- **HML (Homologação)**: Branch `release`. Auto-deploy para porta `5001`. Tags GitHub: `hml-v*`.
- **PROD (Produção)**: Branch `main`. Auto-deploy para porta `5000`. Tags GitHub: `v*`.

## CI/CD com GitHub Actions
Os workflows em `.github/workflows/` gerenciam o build e push:
1. `validate-merge.yml`: Garante o fluxo `dev` -> `release` -> `main`.
2. `hml-deploy.yml`: Disparado no push para `release`. Gera tag `hml-vX.Y.Z`.
3. `prod-deploy.yml`: Disparado no push para `main`. Gera tag `vX.Y.Z`.

## Configuração do Docker
Utilize os arquivos específicos para cada ambiente:
- `docker-compose.hml.yml`: Configurado para homologação.
- `docker-compose.prod.yml`: Configurado para produção.

Certifique-se de configurar o `UPDATE_TOKEN` e a `SECRET_KEY` nos segredos do repositório ou no arquivo `.env` do servidor.

## Como Atualizar
1. **Pela UI**: Usuários Admin verão um modal de atualização quando uma nova tag (compatível com o ambiente) for detectada no GitHub.
2. **Mais Tarde**: Se o usuário optar por "Mais Tarde", uma notificação persistente será criada no banco de dados.
3. **Segurança**: O frontend não chama o updater diretamente. Ele chama o backend (`/api/system/update`), que valida a sessão e o token interno antes de acionar o sidecar.

## Migrações de Banco (Alembic)
As migrações são aplicadas automaticamente pelo sidecar `prp-updater` durante o processo de atualização (`alembic upgrade head`).
- Localmente, use `flask db upgrade` ou execute via docker se necessário.

