import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../api/api_client.dart';
import '../../core/biometric_service.dart';
import '../../core/secure_storage.dart';
import '../../models/mobile_models.dart';

final apiClientProvider = Provider<ApiClient>((ref) => ApiClient());

final authControllerProvider = AsyncNotifierProvider<AuthController, MobileSession?>(
  AuthController.new,
);

class AuthController extends AsyncNotifier<MobileSession?> {
  @override
  Future<MobileSession?> build() async {
    final token = await SecureStorage.readToken();
    if (token == null || token.isEmpty) return null;

    final biometricEnabled = await SecureStorage.readBiometricEnabled();
    if (biometricEnabled) {
      final ok = await BiometricService.authenticate(
        reason: 'Confirme sua biometria para acessar o PRP Mobile.',
      );
      if (!ok) return null;
    }

    return MobileSession(token: token, userName: 'Usuario', email: '');
  }

  Future<void> login(String email, String password) async {
    try {
      final client = ref.read(apiClientProvider);
      final session = await client.login(email, password);
      await SecureStorage.saveToken(session.token);
      state = AsyncData(session);
    } catch (_) {
      state = const AsyncData(null);
      rethrow;
    }
  }

  Future<void> loginWithBiometrics() async {
    try {
      final token = await SecureStorage.readToken();
      if (token == null || token.isEmpty) {
        throw Exception(
          'Nenhuma sessao salva para biometria. Entre com email e senha uma vez.',
        );
      }

      final biometricEnabled = await SecureStorage.readBiometricEnabled();
      if (!biometricEnabled) {
        throw Exception('Biometria desativada. Ative no menu do app.');
      }

      final ok = await BiometricService.authenticate(
        reason: 'Confirme sua biometria para acessar o PRP Mobile.',
      );
      if (!ok) {
        throw Exception('Autenticacao biometrica nao concluida.');
      }

      state = AsyncData(MobileSession(token: token, userName: 'Usuario', email: ''));
    } catch (_) {
      state = const AsyncData(null);
      rethrow;
    }
  }

  Future<void> logout() async {
    await SecureStorage.clearToken();
    state = const AsyncData(null);
  }
}
