import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/secure_storage.dart';

final themeControllerProvider = AsyncNotifierProvider<ThemeController, ThemeMode>(
  ThemeController.new,
);

class ThemeController extends AsyncNotifier<ThemeMode> {
  @override
  Future<ThemeMode> build() async {
    final saved = await SecureStorage.readThemeMode();
    return _fromString(saved);
  }

  Future<void> setThemeMode(ThemeMode mode) async {
    state = AsyncData(mode);
    await SecureStorage.saveThemeMode(_toString(mode));
  }

  ThemeMode _fromString(String? value) {
    switch (value) {
      case 'dark':
        return ThemeMode.dark;
      case 'light':
      default:
        return ThemeMode.light;
    }
  }

  String _toString(ThemeMode mode) {
    return mode == ThemeMode.dark ? 'dark' : 'light';
  }
}
