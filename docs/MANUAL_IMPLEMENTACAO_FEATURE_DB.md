# Manual de Implementacao de Feature com Alteracao de Banco

Este guia e para uso de administradores tecnicos quando uma nova feature exige mudanca de estrutura de banco.

## 1. Objetivo

Garantir rollout seguro de mudancas de schema, com risco minimo de perda de dados e com rollback claro.

## 2. Regra Base

- Toda mudanca de estrutura deve ser versionada por migracao.
- Nunca aplicar mudanca estrutural direto no banco de producao sem validar em HML.
- Sempre ter backup valido antes de qualquer alteracao em PRD.

## 3. Fluxo Recomendado (Expand -> Migrate -> Contract)

1. Expand:
Adicionar nova tabela/coluna sem remover legado.
Evitar mudancas destrutivas nessa etapa.

2. Migrate:
Popular ou converter dados para a nova estrutura.
Scripts devem ser idempotentes (rodar mais de uma vez sem quebrar).

3. Contract:
Remover colunas/tabelas antigas apenas em release posterior, apos validacao operacional.

## 4. Checklist de Pre-Merge

1. Definir impacto:
- Quais tabelas/colunas mudam?
- Qual risco de lock/tempo de execucao?
- Existe necessidade de janela de manutencao?

2. Criar migracao:
- Gerar migracao com Alembic.
- Revisar SQL gerado (indices, constraints, defaults).

3. Compatibilidade da aplicacao:
- Garantir que app atual funcione com schema novo na fase Expand.
- Evitar acoplamento imediato em mudanca destrutiva.

4. Testes:
- CRUD da feature nova.
- Fluxos antigos criticos ainda funcionando.
- Restore de backup em ambiente de teste.

## 5. Checklist de Deploy em HML

1. Publicar imagem da app.
2. Atualizar stack HML.
3. Executar migracao.
4. Validar:
- `/health`
- logs da app
- fluxos de negocio da feature
- fluxos legados impactados
5. Validar backup e restore.

## 6. Checklist de Deploy em PRD

1. Backup obrigatorio antes do deploy.
2. Confirmar tag/version em uso.
3. Aplicar update da app.
4. Executar migracao.
5. Validar:
- `health` da aplicacao
- erros em logs
- consultas/telas principais
6. Registrar horario, versao e resultado.

## 7. Validacoes de Integridade (Pos-Deploy)

- Contagem de registros chave antes/depois.
- Constraints unicas e FKs sem violacao.
- Queries criticas com tempo aceitavel.
- Sem erro 5xx em rotas principais.

## 8. Rollback

Para alteracao estrutural, o rollback preferencial e por restauracao de backup.

Fluxo:
1. Colocar sistema em manutencao (se necessario).
2. Restaurar backup validado.
3. Subir imagem/tag anterior da app.
4. Validar rotas criticas e integridade.

## 9. Padrao de Comunicacao

Antes do deploy:
- Versao
- Mudancas de schema
- Risco
- Plano de rollback

Depois do deploy:
- Resultado (ok/falha)
- Evidencias de validacao
- Pendencias abertas

## 10. Comandos Minimos de Referencia (exemplo)

### Subir stack (HML/PRD)

```bash
docker compose --env-file /caminho/.env.<ambiente> -f docker-compose.<ambiente>.yml up -d
```

### Health

```bash
curl -fsS http://127.0.0.1:5000/health
```

### Logs

```bash
docker compose --env-file /caminho/.env.<ambiente> -f docker-compose.<ambiente>.yml logs --tail=200 <servico>
```
