import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/biometric_service.dart';
import '../../core/secure_storage.dart';

final biometricControllerProvider = AsyncNotifierProvider<BiometricController, bool>(
  BiometricController.new,
);

class BiometricController extends AsyncNotifier<bool> {
  @override
  Future<bool> build() async {
    return SecureStorage.readBiometricEnabled();
  }

  Future<void> enable() async {
    final available = await BiometricService.isAvailable();
    if (!available) {
      throw Exception('Biometria nao disponivel neste dispositivo.');
    }
    final ok = await BiometricService.authenticate(
      reason: 'Confirme sua biometria para ativar acesso biometrico.',
    );
    if (!ok) {
      throw Exception('Autenticacao biometrica nao concluida.');
    }
    await SecureStorage.saveBiometricEnabled(true);
    state = const AsyncData(true);
  }

  Future<void> disable() async {
    await SecureStorage.saveBiometricEnabled(false);
    state = const AsyncData(false);
  }
}
