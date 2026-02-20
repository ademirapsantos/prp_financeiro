# Sistema de CI/CD e Versionamento PRP Financeiro

Este repositório utiliza um fluxo profissional de entrega contínua (CI/CD) com automação de versões SemVer e publicação no GitHub Container Registry (GHCR).

## 1. Fluxo de Trabalho (Git Flow)
As branches seguem regras estritas de promoção:
- **`dev`**: Desenvolvimento local. Cada commit nesta branch **incrementa automaticamente o PATCH** (ex: 1.0.1 -> 1.0.2).
- **`release`**: Homologação (HML). Recebe PRs vindos APENAS da `dev`. Imagens publicadas como `hml-latest`.
- **`main`**: Produção (PRD). Recebe PRs vindos APENAS da `release`. Imagens publicadas como `prod-latest` e versionadas (`vX.Y.Z`).

## 2. Versionamento Automático
Para ativar o incremento automático de versão localmente, você deve configurar o Git para usar os hooks do projeto:

```powershell
# Execute na raiz do repositório
git config core.hooksPath .githooks
```

## 3. Configuração de Manifestos (Versão Latest)
O endpoint `/api/system/latest` busca a versão seguindo esta prioridade:

1.  **Arquivo Local (`MANIFEST_FILE`)**:
    *   Prioridade máxima. Útil para evitar chamadas externas.
    *   Configure no `docker-compose.yml` montando o volume `./manifests:/app/manifests:ro`.
2.  **URL Remota (`MANIFEST_BASE_URL`)**:
    *   Fallback caso o arquivo local não exista.
    *   Monta a URL: `{MANIFEST_BASE_URL}/{ENVIRONMENT}.json`.

## 4. Como Testar no Docker
Para verificar o manifest no container HML:
```bash
docker exec -it prp-financeiro-hml flask shell
# Ou via curl (requer auth):
curl -u admin:password http://localhost:5001/api/system/latest
```
Em caso de erro, verifique os logs: `docker logs prp-financeiro-hml`.

