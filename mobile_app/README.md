# PRP Financeiro Mobile (MVP)

App Flutter cliente leve para consumo da API mobile do PRP Financeiro.

## Escopo MVP
- Login por token em `/api/mobile/auth/login`
- Dashboard compacto
- Lançamentos: listar e criar (compra cartão ou lançamento em conta)
- Cartões/Faturas: visualização
- Títulos/Dívidas: visualização
- Sem liquidação/baixa contábil no mobile

## Requisitos
- Flutter 3.22+
- Backend PRP Financeiro com endpoints `/api/mobile/*`

## Configuração
1. Instale dependências:
```bash
flutter pub get
```

2. Execute definindo URL da API:
```bash
flutter run --dart-define=API_BASE_URL=http://SEU_HOST:5000
```

## Build Android
```bash
flutter build apk --release --dart-define=API_BASE_URL=https://SEU_BACKEND
```

## Estrutura
- `lib/src/api`: cliente HTTP
- `lib/src/features`: telas e estado
- `lib/src/core`: utilitários e constantes

## Segurança
- Token salvo em `flutter_secure_storage` (Keystore/Keychain)
- Cabeçalho `Authorization: Bearer <token>`

## Observações
- Este MVP não implementa modo offline com fila (fase 2).
- O app não substitui rotinas contábeis do web; atua como cliente leve de consulta e alimentação rápida.
