import 'package:flutter_secure_storage/flutter_secure_storage.dart';

class SecureStorage {
  static const _storage = FlutterSecureStorage();
  static const _tokenKey = 'mobile_access_token';
  static const _themeModeKey = 'mobile_theme_mode';
  static const _biometricEnabledKey = 'mobile_biometric_enabled';

  static Future<void> saveToken(String token) => _storage.write(key: _tokenKey, value: token);
  static Future<String?> readToken() => _storage.read(key: _tokenKey);
  static Future<void> clearToken() => _storage.delete(key: _tokenKey);

  static Future<void> saveThemeMode(String mode) => _storage.write(key: _themeModeKey, value: mode);
  static Future<String?> readThemeMode() => _storage.read(key: _themeModeKey);

  static Future<void> saveBiometricEnabled(bool enabled) =>
      _storage.write(key: _biometricEnabledKey, value: enabled ? 'true' : 'false');
  static Future<bool> readBiometricEnabled() async =>
      (await _storage.read(key: _biometricEnabledKey)) == 'true';
}
