import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../../core/ui/state_widgets.dart';
import '../auth/auth_controller.dart';

final titulosProvider = FutureProvider<List<Map<String, dynamic>>>((ref) async {
  final session = ref.watch(authControllerProvider).value;
  if (session == null) throw Exception('Sessao invalida');
  return ref.read(apiClientProvider).getTitulos(session.token);
});

class TitulosPage extends ConsumerWidget {
  const TitulosPage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final money = NumberFormat.currency(locale: 'pt_BR', symbol: 'R\$');
    final state = ref.watch(titulosProvider);
    return state.when(
      loading: () => const LoadingState(),
      error: (e, _) => ErrorState(error: e, onRetry: () => ref.invalidate(titulosProvider)),
      data: (items) => RefreshIndicator(
        onRefresh: () => ref.refresh(titulosProvider.future),
        child: items.isEmpty
            ? ListView(
                children: [
                  SizedBox(height: 120),
                  EmptyState(
                    title: 'Sem dividas abertas',
                    message: 'Nao ha titulos pendentes no momento.',
                    icon: Icons.warning_amber_outlined,
                  ),
                ],
              )
            : ListView.builder(
                padding: const EdgeInsets.all(12),
                itemCount: items.length,
                itemBuilder: (context, index) {
                  final t = items[index];
                  final status = (t['status'] ?? '').toString();
                  return Card(
                    child: ListTile(
                      title: Text(
                        t['descricao'].toString(),
                        style: const TextStyle(fontWeight: FontWeight.w600),
                      ),
                      subtitle: Text('${t['entidade'] ?? '-'} â€¢ Venc: ${t['data_vencimento']}'),
                      trailing: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        crossAxisAlignment: CrossAxisAlignment.end,
                        children: [
                          Text(
                            money.format((t['valor'] ?? 0).toDouble()),
                            style: TextStyle(
                              fontWeight: FontWeight.w700,
                              color: Theme.of(context).colorScheme.error,
                            ),
                          ),
                          const SizedBox(height: 4),
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                            decoration: BoxDecoration(
                              color: Theme.of(context).colorScheme.primary.withValues(alpha: 0.12),
                              borderRadius: BorderRadius.circular(999),
                            ),
                            child: Text(
                              status,
                              style: TextStyle(
                                fontSize: 11,
                                color: Theme.of(context).colorScheme.primary,
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                  );
                },
              ),
      ),
    );
  }
}
