import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../../core/ui/state_widgets.dart';
import '../auth/auth_controller.dart';

final cartoesEFaturasProvider = FutureProvider<Map<String, List<Map<String, dynamic>>>>((ref) async {
  final session = ref.watch(authControllerProvider).value;
  if (session == null) throw Exception('Sessao invalida');
  final api = ref.read(apiClientProvider);
  final cartoes = await api.getCartoes(session.token);
  final faturas = await api.getFaturas(session.token);
  return {'cartoes': cartoes, 'faturas': faturas};
});

class CartoesPage extends ConsumerWidget {
  const CartoesPage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final money = NumberFormat.currency(locale: 'pt_BR', symbol: 'R\$');
    final state = ref.watch(cartoesEFaturasProvider);
    return state.when(
      loading: () => const LoadingState(),
      error: (e, _) => ErrorState(error: e, onRetry: () => ref.invalidate(cartoesEFaturasProvider)),
      data: (data) => RefreshIndicator(
        onRefresh: () => ref.refresh(cartoesEFaturasProvider.future),
        child: ListView(
          padding: const EdgeInsets.all(12),
          children: [
            Text('Cartoes', style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 8),
            if ((data['cartoes'] ?? []).isEmpty)
              const EmptyState(
                title: 'Sem cartoes',
                message: 'Nenhum cartao encontrado para exibicao.',
                icon: Icons.credit_card_off,
              ),
            ...(data['cartoes'] ?? []).map(
              (c) => Card(
                child: ListTile(
                  title: Text(
                    c['nome'].toString(),
                    style: const TextStyle(fontWeight: FontWeight.w600),
                  ),
                  subtitle: Text('Banco: ${c['banco'] ?? '-'}'),
                  trailing: Text(
                    money.format((c['limite_disponivel'] ?? 0).toDouble()),
                    style: TextStyle(
                      fontWeight: FontWeight.w700,
                      color: Theme.of(context).colorScheme.primary,
                    ),
                  ),
                ),
              ),
            ),
            const SizedBox(height: 16),
            Text('Faturas', style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 8),
            if ((data['faturas'] ?? []).isEmpty)
              const EmptyState(
                title: 'Sem faturas abertas',
                message: 'Nao ha faturas pendentes para o periodo.',
                icon: Icons.receipt_outlined,
              ),
            ...(data['faturas'] ?? []).map(
              (f) => Card(
                child: ListTile(
                  title: Text(
                    '${f['cartao_nome']} - ${f['competencia']}',
                    style: const TextStyle(fontWeight: FontWeight.w600),
                  ),
                  subtitle: Text('Vence em ${f['data_vencimento']}'),
                  trailing: Text(
                    money.format((f['pendente'] ?? 0).toDouble()),
                    style: TextStyle(
                      fontWeight: FontWeight.w700,
                      color: Theme.of(context).colorScheme.error,
                    ),
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
