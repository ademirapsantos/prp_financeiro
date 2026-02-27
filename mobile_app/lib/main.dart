import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'src/core/ui/app_theme.dart';
import 'src/features/auth/auth_controller.dart';
import 'src/features/auth/login_page.dart';
import 'src/features/home/home_page.dart';
import 'src/features/theme/theme_controller.dart';

void main() {
  runApp(const ProviderScope(child: PrpMobileApp()));
}

class PrpMobileApp extends ConsumerWidget {
  const PrpMobileApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final authState = ref.watch(authControllerProvider);
    final themeState = ref.watch(themeControllerProvider);
    final themeMode = themeState.valueOrNull ?? ThemeMode.light;
    return MaterialApp(
      title: 'PRP Financeiro Mobile',
      theme: AppTheme.light(),
      darkTheme: AppTheme.dark(),
      themeMode: themeMode,
      home: authState.when(
        loading: () => const _LoadingScreen(),
        error: (_, __) => const LoginPage(),
        data: (session) => session == null ? const LoginPage() : const HomePage(),
      ),
    );
  }
}

class _LoadingScreen extends StatelessWidget {
  const _LoadingScreen();

  @override
  Widget build(BuildContext context) {
    return const Scaffold(body: Center(child: CircularProgressIndicator()));
  }
}
