import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../auth/auth_controller.dart';
import '../biometric/biometric_controller.dart';
import '../cartoes/cartoes_page.dart';
import '../dashboard/dashboard_page.dart';
import '../lancamentos/lancamentos_page.dart';
import '../theme/theme_controller.dart';
import '../titulos/titulos_page.dart';

class HomePage extends ConsumerStatefulWidget {
  const HomePage({super.key});

  @override
  ConsumerState<HomePage> createState() => _HomePageState();
}

class _HomePageState extends ConsumerState<HomePage> {
  int _index = 0;

  @override
  Widget build(BuildContext context) {
    const pages = [
      DashboardPage(),
      LancamentosPage(),
      CartoesPage(),
      TitulosPage(),
    ];

    final biometricState = ref.watch(biometricControllerProvider);
    final biometricEnabled = biometricState.valueOrNull ?? false;
    final biometricBusy = biometricState.isLoading;

    return Scaffold(
      appBar: AppBar(
        title: const Text('PRP Mobile'),
        actions: [
          IconButton(
            tooltip: biometricEnabled ? 'Desativar biometria' : 'Ativar biometria',
            onPressed: biometricBusy ? null : () => _toggleBiometria(biometricEnabled),
            icon: Icon(biometricEnabled ? Icons.fingerprint : Icons.fingerprint_outlined),
          ),
          PopupMenuButton<ThemeMode>(
            tooltip: 'Tema',
            icon: const Icon(Icons.palette_outlined),
            onSelected: (mode) => ref.read(themeControllerProvider.notifier).setThemeMode(mode),
            itemBuilder: (context) => const [
              PopupMenuItem(value: ThemeMode.light, child: Text('Tema claro')),
              PopupMenuItem(value: ThemeMode.dark, child: Text('Tema escuro')),
            ],
          ),
          IconButton(
            tooltip: 'Fechar app',
            onPressed: () => SystemNavigator.pop(),
            icon: const Icon(Icons.close),
          ),
          PopupMenuButton<String>(
            tooltip: 'Conta',
            icon: const Icon(Icons.more_vert),
            onSelected: (value) async {
              if (value == 'logout') {
                await ref.read(authControllerProvider.notifier).logout();
              }
            },
            itemBuilder: (context) => const [
              PopupMenuItem(
                value: 'logout',
                child: Text('Encerrar sessao'),
              ),
            ],
          ),
        ],
      ),
      body: pages[_index],
      bottomNavigationBar: NavigationBar(
        height: 72,
        selectedIndex: _index,
        onDestinationSelected: (idx) => setState(() => _index = idx),
        destinations: const [
          NavigationDestination(icon: Icon(Icons.dashboard_outlined), label: 'Dashboard'),
          NavigationDestination(icon: Icon(Icons.receipt_long_outlined), label: 'Contas a Pagar'),
          NavigationDestination(icon: Icon(Icons.credit_card_outlined), label: 'Faturas'),
          NavigationDestination(icon: Icon(Icons.warning_amber_outlined), label: 'Dividas'),
        ],
      ),
    );
  }

  Future<void> _toggleBiometria(bool enabled) async {
    try {
      if (enabled) {
        await ref.read(biometricControllerProvider.notifier).disable();
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Biometria desativada.')),
          );
        }
      } else {
        await ref.read(biometricControllerProvider.notifier).enable();
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Biometria ativada com sucesso.')),
          );
        }
      }
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(e.toString().replaceFirst('Exception: ', ''))),
      );
    }
  }
}
