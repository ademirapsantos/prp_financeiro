import 'dart:convert';
import 'dart:async';
import 'dart:io';

import 'package:http/http.dart' as http;

import '../core/env.dart';
import '../models/mobile_models.dart';

class ApiClient {
  static const String _communicationErrorMessage =
      'Falha na comunicacao com o servidor. Tente novamente.';
  final String baseUrl;

  ApiClient({String? baseUrl}) : baseUrl = baseUrl ?? Env.apiBaseUrl;

  Uri _uri(String path, [Map<String, dynamic>? query]) {
    return Uri.parse('$baseUrl$path').replace(
      queryParameters: query?.map((k, v) => MapEntry(k, v.toString())),
    );
  }

  Future<Map<String, dynamic>> _request(
    String method,
    String path, {
    String? token,
    Map<String, dynamic>? query,
    Map<String, dynamic>? body,
  }) async {
    final headers = <String, String>{'Content-Type': 'application/json'};
    if (token != null && token.isNotEmpty) {
      headers['Authorization'] = 'Bearer $token';
    }

    late http.Response res;
    final uri = _uri(path, query);
    try {
      if (method == 'GET') {
        res = await http
            .get(uri, headers: headers)
            .timeout(const Duration(seconds: 20));
      } else {
        res = await http
            .post(uri, headers: headers, body: jsonEncode(body ?? {}))
            .timeout(const Duration(seconds: 20));
      }
    } on TimeoutException {
      throw Exception(_communicationErrorMessage);
    } on SocketException {
      throw Exception(_communicationErrorMessage);
    } on http.ClientException {
      throw Exception(_communicationErrorMessage);
    } catch (_) {
      throw Exception(_communicationErrorMessage);
    }

    Map<String, dynamic> json;
    try {
      json = jsonDecode(res.body) as Map<String, dynamic>;
    } catch (_) {
      throw Exception('Falha na comunicacao com o servidor. Resposta invalida.');
    }

    if (res.statusCode >= 400 || json['status'] == 'error') {
      throw Exception((json['message'] ?? 'Erro de API').toString());
    }
    return (json['data'] as Map<String, dynamic>? ?? {});
  }

  Future<MobileSession> login(String email, String password) async {
    final data = await _request(
      'POST',
      '/api/mobile/auth/login',
      body: {'email': email, 'password': password},
    );
    final user = data['user'] as Map<String, dynamic>? ?? {};
    return MobileSession(
      token: (data['access_token'] ?? '').toString(),
      userName: (user['nome'] ?? '').toString(),
      email: (user['email'] ?? '').toString(),
    );
  }

  Future<DashboardData> getDashboard(
    String token, {
    required int ano,
    required int mes,
  }) async {
    final data = await _request(
      'GET',
      '/api/mobile/dashboard',
      token: token,
      query: {'ano': ano, 'mes': mes},
    );
    return DashboardData.fromJson(data);
  }

  Future<List<MobileLancamento>> getLancamentos(String token) async {
    final data = await _request('GET', '/api/mobile/lancamentos', token: token);
    final items = List<Map<String, dynamic>>.from(data['items'] as List? ?? []);
    return items.map(MobileLancamento.fromJson).toList();
  }

  Future<void> createLancamentoCartao({
    required String token,
    required String data,
    required String valor,
    required String descricao,
    required String cartaoId,
    required String categoriaId,
  }) async {
    await _request(
      'POST',
      '/api/mobile/lancamentos',
      token: token,
      body: {
        'meio': 'cartao',
        'data': data,
        'valor': valor,
        'descricao': descricao,
        'cartao_id': cartaoId,
        'categoria_id': categoriaId,
      },
    );
  }

  Future<void> createLancamentoConta({
    required String token,
    required String data,
    required String valor,
    required String descricao,
    required String entidadeId,
    required String tipoMovimentacao,
  }) async {
    await _request(
      'POST',
      '/api/mobile/lancamentos',
      token: token,
      body: {
        'meio': 'conta',
        'data': data,
        'valor': valor,
        'descricao': descricao,
        'entidade_id': entidadeId,
        'tipo_movimentacao': tipoMovimentacao,
      },
    );
  }

  Future<Map<String, dynamic>> getLancamentosMeta(String token) async {
    return _request('GET', '/api/mobile/lancamentos/meta', token: token);
  }

  Future<List<Map<String, dynamic>>> getCartoes(String token) async {
    final data = await _request('GET', '/api/mobile/cartoes', token: token);
    return List<Map<String, dynamic>>.from(data['items'] as List? ?? []);
  }

  Future<List<Map<String, dynamic>>> getFaturas(
    String token, {
    int? ano,
    int? mes,
  }) async {
    final mesParam = (ano != null && mes != null)
        ? '${ano.toString().padLeft(4, '0')}-${mes.toString().padLeft(2, '0')}'
        : null;
    final data = await _request(
      'GET',
      '/api/mobile/faturas',
      token: token,
      query: {'status': 'aberta', if (mesParam != null) 'mes': mesParam},
    );
    return List<Map<String, dynamic>>.from(data['items'] as List? ?? []);
  }

  Future<List<Map<String, dynamic>>> getTitulos(String token) async {
    final data = await _request(
      'GET',
      '/api/mobile/titulos',
      token: token,
      query: {'status': 'vencido'},
    );
    return List<Map<String, dynamic>>.from(data['items'] as List? ?? []);
  }

  Future<Map<String, dynamic>> getDashboardDespesasMesDetalhe(
    String token, {
    required int ano,
    required int mes,
  }) {
    return _request(
      'GET',
      '/api/mobile/dashboard/despesas-mes-detalhe',
      token: token,
      query: {'ano': ano, 'mes': mes},
    );
  }
}

