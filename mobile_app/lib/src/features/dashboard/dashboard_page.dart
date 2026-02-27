import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../../core/ui/app_theme.dart';
import '../../core/ui/state_widgets.dart';
import '../../models/mobile_models.dart';
import '../auth/auth_controller.dart';

final selectedMonthProvider = StateProvider<int>((ref) => DateTime.now().month);

final dashboardProvider = FutureProvider.family<DashboardData, ({int ano, int mes})>((ref, comp) async {
  final session = ref.watch(authControllerProvider).value;
  if (session == null) throw Exception('Sessao invalida');
  final client = ref.read(apiClientProvider);
  return client.getDashboard(session.token, ano: comp.ano, mes: comp.mes);
});

class DashboardPage extends ConsumerWidget {
  const DashboardPage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final anoSelecionado = DateTime.now().year;
    final mesSelecionado = ref.watch(selectedMonthProvider);
    final state = ref.watch(dashboardProvider((ano: anoSelecionado, mes: mesSelecionado)));
    final money = NumberFormat.currency(locale: 'pt_BR', symbol: 'R\$');

    return state.when(
      loading: () => const LoadingState(),
      error: (e, _) => ErrorState(error: e),
      data: (data) => Column(
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 16, 16, 8),
            child: Column(
              children: [
                DropdownButtonFormField<int>(
                  value: mesSelecionado,
                  decoration: const InputDecoration(labelText: 'Mes'),
                  items: List.generate(
                    12,
                    (i) => DropdownMenuItem(
                      value: i + 1,
                      child: Text(_monthLabel(i + 1)),
                    ),
                  ),
                  onChanged: (v) {
                    if (v != null) ref.read(selectedMonthProvider.notifier).state = v;
                  },
                ),
                const SizedBox(height: 12),
                _InfoCard(
                  title: 'Total Pendente (Cartoes)',
                  value: money.format(data.totalPendenteCartoes),
                  icon: Icons.credit_card,
                  color: AppColors.warning,
                  onTap: () => Navigator.of(context).push(
                    MaterialPageRoute(
                      builder: (_) => _DashboardDetalhePage(
                        title: 'Total Pendente (Cartoes)',
                        kind: _DashboardDetalheKind.cartoesPendentes,
                        ano: anoSelecionado,
                        mes: mesSelecionado,
                      ),
                    ),
                  ),
                ),
                _InfoCard(
                  title: 'Total Despesas no Mes',
                  value: money.format(data.totalDespesasMes),
                  icon: Icons.trending_down,
                  color: AppColors.danger,
                  onTap: () => Navigator.of(context).push(
                    MaterialPageRoute(
                      builder: (_) => _DashboardDetalhePage(
                        title: 'Total Despesas no Mes',
                        kind: _DashboardDetalheKind.despesasMes,
                        ano: anoSelecionado,
                        mes: mesSelecionado,
                      ),
                    ),
                  ),
                ),
                const SizedBox(height: 8),
                Align(
                  alignment: Alignment.centerLeft,
                  child: Text('Proximos Vencimentos', style: Theme.of(context).textTheme.titleMedium),
                ),
              ],
            ),
          ),
          Expanded(
            child: RefreshIndicator(
              onRefresh: () => ref.refresh(
                dashboardProvider((ano: anoSelecionado, mes: mesSelecionado)).future,
              ),
              child: ListView(
                padding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
                children: [
                  const SizedBox(height: 8),
                  if (data.proximosVencimentos.isEmpty)
                    const EmptyState(
                      title: 'Sem vencimentos',
                      message: 'Nao ha registros para exibir no momento.',
                      icon: Icons.event_available,
                    ),
                  ...data.proximosVencimentos.map(
                    (item) {
                      final venc = DateTime.tryParse((item['vencimento'] ?? '').toString());
                      final today = DateTime.now();
                      final overdue = venc != null &&
                          DateTime(venc.year, venc.month, venc.day)
                              .isBefore(DateTime(today.year, today.month, today.day));
                      return Card(
                        child: ListTile(
                          title: Text((item['descricao'] ?? '').toString()),
                          subtitle: Text('Venc.: ${(item['vencimento'] ?? '').toString()}'),
                          trailing: Column(
                            mainAxisAlignment: MainAxisAlignment.center,
                            crossAxisAlignment: CrossAxisAlignment.end,
                            children: [
                              Text(
                                money.format((item['valor'] ?? 0).toDouble()),
                                style: const TextStyle(fontWeight: FontWeight.w700),
                              ),
                              const SizedBox(height: 4),
                              Container(
                                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                                decoration: BoxDecoration(
                                  color: overdue ? AppColors.danger.withValues(alpha: 0.12) : AppColors.success.withValues(alpha: 0.12),
                                  borderRadius: BorderRadius.circular(999),
                                ),
                                child: Text(
                                  overdue ? 'Vencido' : 'A vencer',
                                  style: TextStyle(
                                    fontSize: 11,
                                    color: overdue ? AppColors.danger : AppColors.success,
                                  ),
                                ),
                              ),
                            ],
                          ),
                        ),
                      );
                    },
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  static String _monthLabel(int month) {
    const names = [
      'Janeiro',
      'Fevereiro',
      'Marco',
      'Abril',
      'Maio',
      'Junho',
      'Julho',
      'Agosto',
      'Setembro',
      'Outubro',
      'Novembro',
      'Dezembro',
    ];
    return names[month - 1];
  }
}

class _InfoCard extends StatelessWidget {
  final String title;
  final String value;
  final IconData icon;
  final Color color;
  final VoidCallback? onTap;

  const _InfoCard({
    required this.title,
    required this.value,
    required this.icon,
    required this.color,
    this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      child: ListTile(
        leading: CircleAvatar(
          backgroundColor: color.withValues(alpha: 0.14),
          foregroundColor: color,
          child: Icon(icon),
        ),
        title: Text(title, style: const TextStyle(fontWeight: FontWeight.w600)),
        subtitle: Text(
          value,
          style: Theme.of(context).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w800),
        ),
        onTap: onTap,
      ),
    );
  }
}

enum _DashboardDetalheKind { cartoesPendentes, despesasMes }

class _DashboardDetalhePage extends ConsumerWidget {
  final String title;
  final _DashboardDetalheKind kind;
  final int ano;
  final int mes;

  const _DashboardDetalhePage({
    required this.title,
    required this.kind,
    required this.ano,
    required this.mes,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final money = NumberFormat.currency(locale: 'pt_BR', symbol: 'R\$');
    final session = ref.watch(authControllerProvider).value;
    if (session == null) {
      return const Scaffold(body: Center(child: Text('Sessao invalida')));
    }

    return Scaffold(
      appBar: AppBar(title: Text(title)),
      body: FutureBuilder<_DashboardDetalheData>(
        future: _loadData(ref, session.token),
        builder: (context, snapshot) {
          if (snapshot.connectionState != ConnectionState.done) {
            return const Center(child: CircularProgressIndicator());
          }
          if (snapshot.hasError) {
            return Center(child: Text(snapshot.error.toString()));
          }
          final data = snapshot.data ?? const _DashboardDetalheData(items: [], total: 0);
          return Column(
            children: [
              Expanded(
                child: ListView.builder(
                  padding: const EdgeInsets.all(12),
                  itemCount: data.items.length,
                  itemBuilder: (context, index) {
                    final item = data.items[index];
                    return Card(
                      child: ListTile(
                        title: Text(item['descricao']?.toString() ?? ''),
                        subtitle: Text(item['data']?.toString() ?? ''),
                        trailing: Text(money.format((item['valor'] ?? 0).toDouble())),
                      ),
                    );
                  },
                ),
              ),
              Padding(
                padding: const EdgeInsets.fromLTRB(16, 8, 16, 4),
                child: Align(
                  alignment: Alignment.centerRight,
                  child: Text(
                    'Total: ${money.format(data.total)}',
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                ),
              ),
              Padding(
                padding: const EdgeInsets.all(16),
                child: SizedBox(
                  width: double.infinity,
                  child: OutlinedButton(
                    onPressed: () => Navigator.of(context).pop(),
                    child: const Text('Voltar'),
                  ),
                ),
              ),
            ],
          );
        },
      ),
    );
  }

  Future<_DashboardDetalheData> _loadData(WidgetRef ref, String token) async {
    final api = ref.read(apiClientProvider);
    if (kind == _DashboardDetalheKind.cartoesPendentes) {
      final faturas = await api.getFaturas(token, ano: ano, mes: mes);
      final items = faturas
          .map(
            (f) => <String, dynamic>{
              'descricao': 'Fatura ${f['cartao_nome'] ?? ''} (${f['competencia'] ?? ''})',
              'data': (f['data_vencimento'] ?? '').toString(),
              'valor': (f['pendente'] ?? 0).toDouble(),
            },
          )
          .toList();
      final total = items.fold<double>(0, (acc, e) => acc + (e['valor'] as double));
      return _DashboardDetalheData(items: items, total: total);
    }

    final detalhe = await api.getDashboardDespesasMesDetalhe(
      token,
      ano: ano,
      mes: mes,
    );
    final items = List<Map<String, dynamic>>.from(detalhe['items'] as List? ?? []);
    final total = (detalhe['total'] ?? 0).toDouble();
    return _DashboardDetalheData(items: items, total: total);
  }
}

class _DashboardDetalheData {
  final List<Map<String, dynamic>> items;
  final double total;

  const _DashboardDetalheData({required this.items, required this.total});
}
