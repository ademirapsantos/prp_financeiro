# API Mobile - PRP Financeiro

Base: `/api/mobile`

## Autenticação

### `POST /api/mobile/auth/login`
Request:
```json
{
  "email": "user@email.com",
  "password": "senha"
}
```

Response:
```json
{
  "status": "success",
  "message": "Login efetuado com sucesso.",
  "data": {
    "access_token": "....",
    "token_type": "Bearer",
    "expires_in": 604800,
    "user": {
      "id": "...",
      "nome": "Administrador",
      "email": "user@email.com",
      "is_admin": true,
      "deve_alterar_senha": false
    }
  }
}
```

Use `Authorization: Bearer <token>` nos demais endpoints.

## Endpoints MVP

- `GET /api/mobile/dashboard`
- `GET /api/mobile/lancamentos`
- `POST /api/mobile/lancamentos`
- `GET /api/mobile/lancamentos/meta`
- `GET /api/mobile/cartoes`
- `GET /api/mobile/faturas?status=aberta|todas&mes=YYYY-MM`
- `GET /api/mobile/faturas/{id}`
- `GET /api/mobile/titulos?status=aberto|vencido`
- `GET /api/mobile/titulos/{id}`

## Regras

- Não há liquidação de títulos por API mobile.
- Não há pagamento de fatura por API mobile.
- Criação de lançamento:
  - `meio=cartao`: usa regras de compra em cartão existentes.
  - `meio=conta`: usa `registrar_movimentacao_outros` existente.
- Payload rejeita campos não esperados.
