# Sistema de Atualização Manual/Automático

O PRP Financeiro agora possui um sistema de atualização in-app seguro.

## Configuração do Sidecar (prp-updater)
No seu `docker-compose.yml`, certifique-se de que o serviço `prp-updater` está configurado corretamente:
- volume: `/var/run/docker.sock:/var/run/docker.sock`
- variavel: `UPDATE_TOKEN=sua_chave_segura`

## Como disparar uma atualização
1. Pela UI: O sistema detectará uma nova versão (ex: via Release do GitHub) e mostrará um banner.
2. Manualmente via API:
   `POST http://host:5005/api/update`
   Header: `Authorization: Bearer sua_chave_segura`

## Migrações de Banco (Alembic)
Todas as atualizações de banco de dados agora são feitas via Alembic.
O updater executará automaticamente `alembic upgrade head` antes de reiniciar os containers.

### Criando novas migrações (Desenvolvedor)
Se você alterou os modelos em `models.py`, rode:
`alembic revision --autogenerate -m "descrição da mudança"`
O arquivo gerado deve ser comitado ao repositório.
