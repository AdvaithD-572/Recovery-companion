import '../../core/config/api_config.dart';
import 'dart:convert';
import 'dart:async';
import 'package:uuid/uuid.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:http/http.dart' as http;

class ApiClient {
  final String baseUrl;
  final FlutterSecureStorage storage;
  final http.Client _client = http.Client();

  ApiClient({required this.storage, this.baseUrl = ApiConfig.baseUrl});
  String storageKey(String name) =>
      baseUrl == 'http://10.0.2.2:8000' ? name : '$baseUrl|$name';
  void close() => _client.close();

  Future<Map<String, String>> _getHeaders({bool requiresAuth = true}) async {
    final headers = <String, String>{
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    };

    if (requiresAuth) {
      final token = await storage.read(key: storageKey('access_token'));
      if (token != null) {
        headers['Authorization'] = 'Bearer $token';
      }
    }
    return headers;
  }

  Future<dynamic> get(String endpoint,
      {Map<String, String>? queryParams}) async {
    final uri =
        Uri.parse('$baseUrl$endpoint').replace(queryParameters: queryParams);
    final headers = await _getHeaders();

    final response = await _client
        .get(uri, headers: headers)
        .timeout(const Duration(seconds: 10));
    return _handleResponse(response);
  }

  Future<List<dynamic>> medicines() async {
    final owner = await account();
    if (owner == null) throw UnauthorizedException('Sign in to view medicines');
    final key = storageKey('medicines:$owner');
    final headers = await _ownerHeaders(owner);
    try {
      final response = await _client
          .get(Uri.parse('$baseUrl/api/v1/prescriptions/'), headers: headers)
          .timeout(const Duration(seconds: 10));
      final rows = List<dynamic>.from(_handleResponse(response));
      await storage.write(
          key: key,
          value: jsonEncode(
              {'at': DateTime.now().toUtc().toIso8601String(), 'rows': rows}));
      return rows;
    } on http.ClientException {
      return _cachedMedicines(key);
    } on TimeoutException {
      return _cachedMedicines(key);
    }
  }

  Future<List<dynamic>> _cachedMedicines(String key) async {
    final raw = await storage.read(key: key);
    if (raw == null)
      throw ApiException('Connect once to download your medicines');
    final cache = jsonDecode(raw);
    return [
      for (final row in cache['rows']) {...row, '_cachedAt': cache['at']}
    ];
  }

  static const diaryPaths = {
    '/api/v1/logs/daily': 'daily',
    '/api/v1/food/log': 'meal',
    '/api/v1/prescriptions/dose-log': 'dose'
  };
  Future<String?> account() async {
    final token = await getAccessToken();
    if (token == null) return null;
    return jsonDecode(utf8.decode(
            base64Url.decode(base64Url.normalize(token.split('.')[1]))))['sub']
        as String?;
  }

  Future<dynamic> post(String endpoint, {Map<String, dynamic>? body}) async {
    final kind = diaryPaths[endpoint];
    if (kind == null) return _post(endpoint, body: body);
    final owner = await account();
    if (owner == null) {
      throw UnauthorizedException('Sign in to save a diary entry');
    }
    final id = const Uuid().v4();
    final event = {
      'id': id,
      'kind': kind,
      'occurred': DateTime.now().toUtc().toIso8601String(),
      'payload': body
    };
    final key = storageKey('diary:$owner:$id');
    await storage.write(key: key, value: jsonEncode(event));
    try {
      await _sendEvent(key, event, owner);
      return {'saved': true};
    } on http.ClientException {
      return {'queued': true};
    } on TimeoutException {
      return {'queued': true};
    } on ApiException catch (e) {
      if (e is ConflictException) await storage.delete(key: key);
      rethrow;
    }
  }

  Future<void> _sendEvent(
      String key, Map<String, dynamic> event, String owner) async {
    final headers = await _ownerHeaders(owner);
    final response = await _client
        .post(Uri.parse('$baseUrl/api/v1/care/sync'),
            headers: headers, body: jsonEncode(event))
        .timeout(const Duration(seconds: 12));
    _handleResponse(response);
    await storage.delete(key: key);
  }

  Future<Map<String, String>> _ownerHeaders(String owner) async {
    final headers = await _getHeaders();
    final access = headers['Authorization']?.split(' ').last;
    if (access == null ||
        jsonDecode(utf8.decode(base64Url
                .decode(base64Url.normalize(access.split('.')[1]))))['sub'] !=
            owner) {
      throw UnauthorizedException('Account changed');
    }
    return headers;
  }

  Future<int> syncDiary() async {
    final owner = await account();
    if (owner == null) return 0;
    final queue = (await storage.readAll())
        .entries
        .where((item) => item.key.startsWith(storageKey('diary:$owner:')))
        .toList();
    for (final item in queue) {
      try {
        await _sendEvent(
            item.key, Map<String, dynamic>.from(jsonDecode(item.value)), owner);
      } on http.ClientException {
        break;
      } on TimeoutException {
        break;
      } on ApiException {
        continue;
      }
    }
    return (await storage.readAll())
        .keys
        .where((key) => key.startsWith(storageKey('diary:$owner:')))
        .length;
  }

  Future<dynamic> _post(String endpoint, {Map<String, dynamic>? body}) async {
    final uri = Uri.parse('$baseUrl$endpoint');
    final headers = await _getHeaders();

    final response = await _client.post(
      uri,
      headers: headers,
      body: body != null ? jsonEncode(body) : null,
    );
    return _handleResponse(response);
  }

  Future<dynamic> patch(String endpoint, {Map<String, dynamic>? body}) async {
    final uri = Uri.parse('$baseUrl$endpoint');
    final headers = await _getHeaders();

    final response = await _client.patch(
      uri,
      headers: headers,
      body: body != null ? jsonEncode(body) : null,
    );
    return _handleResponse(response);
  }

  Future<dynamic> delete(String endpoint) async {
    final uri = Uri.parse('$baseUrl$endpoint');
    final headers = await _getHeaders();

    final response = await _client.delete(uri, headers: headers);
    return _handleResponse(response);
  }

  Future<dynamic> uploadFile(
    String endpoint,
    List<int> fileBytes,
    String fileName,
    String fieldName, {
    Map<String, String>? fields,
    String? mimeType,
  }) async {
    final uri = Uri.parse('$baseUrl$endpoint');
    final headers = await _getHeaders();
    // Remove content-type so multipart boundary is set automatically
    headers.remove('Content-Type');

    final request = http.MultipartRequest('POST', uri);
    request.headers.addAll(headers);
    if (fields != null) {
      request.fields.addAll(fields);
    }

    final mediaType = mimeType != null ? _parseMediaType(mimeType) : null;

    request.files.add(http.MultipartFile.fromBytes(
      fieldName,
      fileBytes,
      filename: fileName,
      contentType: mediaType,
    ));

    final streamedResponse = await request.send();
    final response = await http.Response.fromStream(streamedResponse);
    return _handleResponse(response);
  }

  /// Parse a MIME type string like "image/jpeg" into MediaType
  http.MediaType? _parseMediaType(String mime) {
    try {
      final parts = mime.split('/');
      if (parts.length == 2) return http.MediaType(parts[0], parts[1]);
    } catch (_) {}
    return null;
  }

  dynamic _handleResponse(http.Response response) {
    if (response.statusCode >= 200 && response.statusCode < 300) {
      if (response.body.isEmpty) return null;
      return jsonDecode(utf8.decode(response.bodyBytes));
    } else if (response.statusCode == 401) {
      throw UnauthorizedException('Session expired');
    } else if (response.statusCode == 409) {
      throw ConflictException('Conflict: ${response.body}');
    } else {
      throw ApiException('API error: ${response.statusCode}', response.body);
    }
  }

  Future<void> setTokens(String accessToken, String refreshToken) async {
    await storage.write(key: storageKey('access_token'), value: accessToken);
    await storage.write(key: storageKey('refresh_token'), value: refreshToken);
  }

  Future<void> clearTokens() async {
    await storage.delete(key: storageKey('access_token'));
    await storage.delete(key: storageKey('refresh_token'));
  }

  Future<String?> getAccessToken() async {
    return await storage.read(key: storageKey('access_token'));
  }
}

class ApiException implements Exception {
  final String message;
  final String? details;
  ApiException(this.message, [this.details]);
  @override
  String toString() => message;
}

class UnauthorizedException extends ApiException {
  UnauthorizedException(super.message);
}

class ConflictException extends ApiException {
  ConflictException(super.message);
}
