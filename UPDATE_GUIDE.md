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

1.  **URL Remota (`MANIFEST_BASE_URL`)**:
    *   Fonte principal e automática.
    *   Monta a URL: `{MANIFEST_BASE_URL}/{ENVIRONMENT}.json` (ex: `https://ademirapsantos.github.io/prp_financeiro/hml.json`).
2.  **Arquivo Local (`MANIFEST_FILE`)**:
    *   Fallback ou uso em ambiente isolado (dev).
    *   Se configurado, busca o JSON localmente em `/app/manifests/`.

## 4. Como Testar
Para verificar o manifest no container HML via curl:
```bash
curl -i http://localhost:5001/api/system/latest
```

### Exemplo de Retorno Automático:
Após um push em `release`, o retorno esperado é:
```json
{
  "current_version": "1.4.0",
  "latest_version": "1.4.1",
  "is_new": true,
  "source": "url:https://ademirapsantos.github.io/prp_financeiro/hml.json",
  "environment": "hml"
}
```
> [!NOTE]
> `/api/system/latest` e `/api/version` são públicos para permitir que o frontend e o sistema de notificação verifiquem atualizações sem exigir login prévio.

Em caso de erro, verifique os logs: `docker logs prp-financeiro-hml`.
