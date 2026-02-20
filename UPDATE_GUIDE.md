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

Isso ativará o `pre-commit` que executa `tools/bump_version.py` quando você está na branch `dev`.

## 3. CI/CD e Manifestos
O workflow `.github/workflows/publish-ghcr.yml` realiza o build e publica:
1. Imagem Docker no GHCR.
2. Manifesto de versão (`hml.json` ou `prod.json`) na branch `gh-pages`.
   - **URL do Manifesto**: `https://ademirapsantos.github.io/prp_financeiro/hml.json` (ou `prod.json`)

## 4. Atualização In-App
A aplicação consulta o manifesto correspondente ao `ENVIRONMENT` configurado no `docker-compose.yml`.
- Se uma nova versão for detectada, um modal centralizado aparecerá para o Admin.
- O backend chama o sidecar `updater` internamente usando o `UPDATE_TOKEN`.

## 5. Regras de Proteção de Branch (GitHub)
Recomenda-se configurar no GitHub:
- **Branch `main`**: 
  - Exigir PR antes do merge.
  - Exigir que o check `Validate Merge Source` passe (impede merges que não venham de `release`).
- **Branch `release`**:
  - Exigir PR antes do merge.
  - Exigir que o check `Validate Merge Source` passe (impede merges que não venham de `dev`).

## 6. Docker Compose
- `docker-compose.hml.yml`: Porta 5001, Ambiente HML.
- `docker-compose.prod.yml`: Porta 5000, Ambiente PROD.

