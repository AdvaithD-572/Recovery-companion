import 'dart:convert';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:http/http.dart' as http;

class ApiClient {
  static const String baseUrl = 'http://10.97.118.201:8000'; // Windows host IP for physical device
  // static const String baseUrl = 'http://localhost:8000'; // iOS simulator
  
  final FlutterSecureStorage storage;
  final http.Client _client = http.Client();

  ApiClient({required this.storage});

  Future<Map<String, String>> _getHeaders({bool requiresAuth = true}) async {
    final headers = <String, String>{
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    };
    
    if (requiresAuth) {
      final token = await storage.read(key: 'access_token');
      if (token != null) {
        headers['Authorization'] = 'Bearer $token';
      }
    }
    return headers;
  }

  Future<dynamic> get(String endpoint, {Map<String, String>? queryParams}) async {
    final uri = Uri.parse('$baseUrl$endpoint').replace(queryParameters: queryParams);
    final headers = await _getHeaders();
    
    final response = await _client.get(uri, headers: headers);
    return _handleResponse(response);
  }

  Future<dynamic> post(String endpoint, {Map<String, dynamic>? body}) async {
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

    final mediaType = mimeType != null
        ? _parseMediaType(mimeType)
        : null;

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
      return jsonDecode(response.body);
    } else if (response.statusCode == 401) {
      throw UnauthorizedException('Session expired');
    } else if (response.statusCode == 409) {
      throw ConflictException('Conflict: ${response.body}');
    } else {
      throw ApiException('API error: ${response.statusCode}', response.body);
    }
  }

  Future<void> setTokens(String accessToken, String refreshToken) async {
    await storage.write(key: 'access_token', value: accessToken);
    await storage.write(key: 'refresh_token', value: refreshToken);
  }

  Future<void> clearTokens() async {
    await storage.delete(key: 'access_token');
    await storage.delete(key: 'refresh_token');
  }

  Future<String?> getAccessToken() async {
    return await storage.read(key: 'access_token');
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
