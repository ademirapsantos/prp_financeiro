import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../../core/ui/state_widgets.dart';
import '../../models/mobile_models.dart';
import '../auth/auth_controller.dart';
import '../dashboard/dashboard_page.dart';

final lancamentosProvider = FutureProvider<List<MobileLancamento>>((ref) async {
  final session = ref.watch(authControllerProvider).value;
  if (session == null) throw Exception('Sessao invalida');
  return ref.read(apiClientProvider).getLancamentos(session.token);
});

class LancamentosPage extends ConsumerWidget {
  const LancamentosPage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final state = ref.watch(lancamentosProvider);
    final money = NumberFormat.currency(locale: 'pt_BR', symbol: 'R\$');
    return Scaffold(
      body: state.when(
        loading: () => const LoadingState(),
        error: (e, _) => ErrorState(error: e, onRetry: () => ref.invalidate(lancamentosProvider)),
        data: (items) => RefreshIndicator(
          onRefresh: () => ref.refresh(lancamentosProvider.future),
          child: items.isEmpty
              ? ListView(
                  children: [
                    SizedBox(height: 120),
                    EmptyState(
                      title: 'Sem contas a pagar',
                      message: 'Adicione um novo lancamento para comecar.',
                      icon: Icons.receipt_long_outlined,
                    ),
                  ],
                )
              : ListView.builder(
                  padding: const EdgeInsets.all(12),
                  itemCount: items.length,
                  itemBuilder: (context, index) {
                    final item = items[index];
                    return Card(
                      child: ListTile(
                        contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
                        title: Text(
                          item.descricao,
                          style: const TextStyle(fontWeight: FontWeight.w600),
                        ),
                        subtitle: Text('${item.data} â€¢ ${item.meio.toUpperCase()}'),
                        trailing: Text(
                          money.format(item.valor),
                          style: TextStyle(
                            fontWeight: FontWeight.w700,
                            color: Theme.of(context).colorScheme.error,
                          ),
                        ),
                      ),
                    );
                  },
                ),
        ),
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () async {
          await showModalBottomSheet<void>(
            context: context,
            isScrollControlled: true,
            showDragHandle: true,
            shape: const RoundedRectangleBorder(
              borderRadius: BorderRadius.vertical(top: Radius.circular(22)),
            ),
            builder: (_) => const _NovoLancamentoSheet(),
          );
          ref.invalidate(lancamentosProvider);
        },
        icon: const Icon(Icons.add),
        label: const Text('Novo'),
      ),
    );
  }
}

class _NovoLancamentoSheet extends ConsumerStatefulWidget {
  const _NovoLancamentoSheet();

  @override
  ConsumerState<_NovoLancamentoSheet> createState() => _NovoLancamentoSheetState();
}

class _NovoLancamentoSheetState extends ConsumerState<_NovoLancamentoSheet> {
  final _descricao = TextEditingController();
  final _valor = TextEditingController();
  DateTime? _dataConta;
  String _meio = 'cartao';
  String? _cartaoId;
  String? _categoriaId;
  String? _entidadeId;
  String _tipoMov = 'pagar';
  bool _saving = false;
  bool _metaDefaultsApplied = false;

  @override
  Widget build(BuildContext context) {
    final session = ref.watch(authControllerProvider).value;
    if (session == null) return const SizedBox.shrink();

    final metaAsync = ref.watch(_lancamentosMetaProvider(session.token));
    return Padding(
      padding: EdgeInsets.only(
        left: 16,
        right: 16,
        top: 16,
        bottom: MediaQuery.of(context).viewInsets.bottom + 16,
      ),
      child: metaAsync.when(
        loading: () => const SizedBox(height: 180, child: Center(child: CircularProgressIndicator())),
        error: (e, _) => SizedBox(height: 180, child: Center(child: Text(e.toString()))),
        data: (meta) {
          _applyMetaDefaults(meta);
          final entidadesFiltradas = _entidadesCompativeis(meta);
          if (entidadesFiltradas.isEmpty) {
            _entidadeId = null;
          }
          if (entidadesFiltradas.isNotEmpty &&
              !entidadesFiltradas.any((e) => e['id'].toString() == (_entidadeId ?? ''))) {
            _entidadeId = entidadesFiltradas.first['id'].toString();
          }
          return Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text('Novo Lancamento', style: Theme.of(context).textTheme.titleMedium),
              const SizedBox(height: 12),
              TextField(controller: _descricao, decoration: const InputDecoration(labelText: 'Descricao')),
              const SizedBox(height: 8),
              TextField(
                controller: _valor,
                decoration: const InputDecoration(labelText: 'Valor (ex: 125,90)'),
                keyboardType: const TextInputType.numberWithOptions(decimal: true),
              ),
              const SizedBox(height: 8),
              InkWell(
                onTap: _meio == 'conta' ? _selecionarDataConta : null,
                child: InputDecorator(
                  decoration: InputDecoration(
                    labelText: 'Data do lancamento',
                    enabled: _meio == 'conta',
                  ),
                  child: Text(
                    _textoDataLancamento(),
                    style: TextStyle(
                      color: _meio == 'conta'
                          ? Theme.of(context).textTheme.bodyMedium?.color
                          : Theme.of(context).disabledColor,
                    ),
                  ),
                ),
              ),
              const SizedBox(height: 8),
              DropdownButtonFormField<String>(
                value: _meio,
                items: const [
                  DropdownMenuItem(value: 'cartao', child: Text('Cartao')),
                  DropdownMenuItem(value: 'conta', child: Text('Conta')),
                ],
                onChanged: (v) => setState(() => _meio = v ?? 'cartao'),
                decoration: const InputDecoration(labelText: 'Meio'),
              ),
              const SizedBox(height: 8),
              if (_meio == 'cartao') ...[
                DropdownButtonFormField<String>(
                  value: _cartaoId,
                  items: (meta['cartoes'] as List<dynamic>)
                      .map((e) => DropdownMenuItem(value: e['id'].toString(), child: Text(e['nome'].toString())))
                      .toList(),
                  onChanged: (v) => setState(() => _cartaoId = v),
                  decoration: const InputDecoration(labelText: 'Cartao'),
                ),
                const SizedBox(height: 8),
                DropdownButtonFormField<String>(
                  value: _categoriaId,
                  items: (meta['categorias_despesa'] as List<dynamic>)
                      .map((e) => DropdownMenuItem(
                            value: e['id'].toString(),
                            child: Text('${e['codigo']} - ${e['nome']}'),
                          ))
                      .toList(),
                  onChanged: (v) => setState(() => _categoriaId = v),
                  decoration: const InputDecoration(labelText: 'Categoria'),
                ),
              ] else ...[
                DropdownButtonFormField<String>(
                  value: _tipoMov,
                  items: const [
                    DropdownMenuItem(value: 'pagar', child: Text('Despesa (Pagar)')),
                    DropdownMenuItem(value: 'receber', child: Text('Receita (Receber)')),
                  ],
                  onChanged: (v) => setState(() => _tipoMov = v ?? 'pagar'),
                  decoration: const InputDecoration(labelText: 'Tipo'),
                ),
                const SizedBox(height: 8),
                if (entidadesFiltradas.isEmpty)
                  const Text(
                    'Nenhuma entidade compativel com o tipo selecionado.',
                    style: TextStyle(color: Colors.orange),
                  ),
                if (entidadesFiltradas.isEmpty) const SizedBox(height: 8),
                DropdownButtonFormField<String>(
                  value: _entidadeId,
                  items: entidadesFiltradas
                      .map((e) => DropdownMenuItem(value: e['id'].toString(), child: Text(e['nome'].toString())))
                      .toList(),
                  onChanged: (v) => setState(() => _entidadeId = v),
                  decoration: const InputDecoration(labelText: 'Entidade'),
                ),
              ],
              const SizedBox(height: 12),
              Align(
                alignment: Alignment.centerRight,
                child: FilledButton(
                  onPressed: _saving ? null : () => _salvar(session.token),
                  child: _saving
                      ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2))
                      : const Text('Salvar'),
                ),
              ),
            ],
          );
        },
      ),
    );
  }

  void _applyMetaDefaults(Map<String, dynamic> meta) {
    if (_metaDefaultsApplied) return;
    _metaDefaultsApplied = true;

    final cartoes = (meta['cartoes'] as List<dynamic>? ?? const []);
    final categorias = (meta['categorias_despesa'] as List<dynamic>? ?? const []);
    final entidades = (meta['entidades'] as List<dynamic>? ?? const []);

    _cartaoId ??= cartoes.isNotEmpty ? cartoes.first['id'].toString() : null;
    _categoriaId ??= categorias.isNotEmpty ? categorias.first['id'].toString() : null;
    _entidadeId ??= entidades.isNotEmpty ? entidades.first['id'].toString() : null;
  }

  List<dynamic> _entidadesCompativeis(Map<String, dynamic> meta) {
    final entidades = (meta['entidades'] as List<dynamic>? ?? const []);
    if (_meio != 'conta') return entidades;

    if (_tipoMov == 'receber') {
      return entidades
          .where((e) =>
              (e is Map<String, dynamic>) &&
              (e['suporta_receber'] == true) &&
              _isTipoEntidadeCompativel(e['tipo'], 'receber'))
          .toList();
    }
    return entidades
        .where((e) =>
            (e is Map<String, dynamic>) &&
            (e['suporta_pagar'] == true) &&
            _isTipoEntidadeCompativel(e['tipo'], 'pagar'))
        .toList();
  }

  bool _isTipoEntidadeCompativel(dynamic tipoRaw, String tipoMovUi) {
    final tipo = (tipoRaw ?? '').toString().trim().toLowerCase();
    if (tipoMovUi == 'pagar') {
      return tipo == 'fornecedor' || tipo == 'outros';
    }
    return tipo == 'cliente' || tipo == 'outros';
  }

  Future<void> _salvar(String token) async {
    final descricao = _descricao.text.trim();
    final valor = _valor.text.trim();

    if (descricao.isEmpty) {
      _showError('Informe a descricao.');
      return;
    }
    if (valor.isEmpty) {
      _showError('Informe o valor.');
      return;
    }
    if (_meio == 'cartao' && ((_cartaoId ?? '').isEmpty || (_categoriaId ?? '').isEmpty)) {
      _showError('Selecione cartao e categoria.');
      return;
    }
    if (_meio == 'conta' && (_entidadeId ?? '').isEmpty) {
      _showError('Selecione entidade.');
      return;
    }
    if (_meio == 'conta' && _dataConta == null) {
      _showError('Informe a data do lancamento.');
      return;
    }

    setState(() => _saving = true);
    final api = ref.read(apiClientProvider);
    final dataLancamento = _meio == 'cartao' ? DateTime.now() : _dataConta!;
    final dateText = DateFormat('yyyy-MM-dd').format(dataLancamento);
    try {
      if (_meio == 'cartao') {
        await api.createLancamentoCartao(
          token: token,
          data: dateText,
          valor: valor,
          descricao: descricao,
          cartaoId: _cartaoId ?? '',
          categoriaId: _categoriaId ?? '',
        );
      } else {
        await api.createLancamentoConta(
          token: token,
          data: dateText,
          valor: valor,
          descricao: descricao,
          entidadeId: _entidadeId ?? '',
          tipoMovimentacao: _tipoMov,
        );
      }
      ref.invalidate(lancamentosProvider);
      final ano = DateTime.now().year;
      final mesSelecionado = ref.read(selectedMonthProvider);
      ref.invalidate(dashboardProvider((ano: ano, mes: mesSelecionado)));
      if (!mounted) return;
      Navigator.of(context).pop();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(e.toString().replaceFirst('Exception: ', ''))),
      );
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  void _showError(String message) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(message)));
  }

  String _textoDataLancamento() {
    if (_meio == 'cartao') {
      return DateFormat('dd/MM/yyyy').format(DateTime.now());
    }
    if (_dataConta == null) return 'Selecione a data';
    return DateFormat('dd/MM/yyyy').format(_dataConta!);
  }

  Future<void> _selecionarDataConta() async {
    final agora = DateTime.now();
    final inicial = _dataConta ?? agora;
    final selecionada = await showDatePicker(
      context: context,
      initialDate: inicial,
      firstDate: DateTime(2000, 1, 1),
      lastDate: DateTime(2100, 12, 31),
    );
    if (selecionada != null && mounted) {
      setState(() => _dataConta = selecionada);
    }
  }
}

final _lancamentosMetaProvider = FutureProvider.family<Map<String, dynamic>, String>((ref, token) async {
  final api = ref.read(apiClientProvider);
  final meta = await api.getLancamentosMeta(token);
  final cartoes = await api.getCartoes(token);
  return {...meta, 'cartoes': cartoes};
});
