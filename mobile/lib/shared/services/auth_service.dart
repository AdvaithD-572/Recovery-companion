import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:hive_flutter/hive_flutter.dart';

import 'api_client.dart';

class AuthUser {
  final String id;
  final String email;
  final String fullName;
  final String role;
  final bool onboardingComplete;

  AuthUser({
    required this.id,
    required this.email,
    required this.fullName,
    required this.role,
    required this.onboardingComplete,
  });

  factory AuthUser.fromJson(Map<String, dynamic> json) {
    return AuthUser(
      id: json['id'] ?? '',
      email: json['email'] ?? '',
      fullName: json['full_name'] ?? '',
      role: json['role'] ?? 'patient',
      onboardingComplete: json['onboarding_complete'] ?? false,
    );
  }
}

class AuthService {
  final ApiClient apiClient;
  final FlutterSecureStorage storage;
  final Box authBox;

  AuthService({
    required this.apiClient,
    required this.storage,
    required this.authBox,
  });

  Future<AuthUser?> getCurrentUser() async {
    final token = await storage.read(key: 'access_token');
    if (token == null) return null;

    try {
      final response = await apiClient.get('/api/v1/patients/me');
      return AuthUser.fromJson(response);
    } catch (e) {
      // Token might be expired, try refresh
      final refreshed = await _refreshToken();
      if (!refreshed) {
        await logout();
        return null;
      }
      final response = await apiClient.get('/api/v1/patients/me');
      return AuthUser.fromJson(response);
    }
  }

  Future<AuthUser> login(String email, String password) async {
    final response = await apiClient.post('/api/v1/auth/patient/login', body: {
      'email': email,
      'password': password,
    });

    await apiClient.setTokens(response['access_token'], response['refresh_token']);
    await authBox.put('role', response['role']);
    
    return AuthUser(
      id: '', // Will be fetched via getCurrentUser
      email: email,
      fullName: '',
      role: response['role'],
      onboardingComplete: false,
    );
  }

  Future<AuthUser> register({
    required String fullName,
    required String email,
    required String password,
    String language = 'en',
  }) async {
    final response = await apiClient.post('/api/v1/auth/patient/register', body: {
      'full_name': fullName,
      'email': email,
      'password': password,
      'preferred_language': language,
    });

    await apiClient.setTokens(response['access_token'], response['refresh_token']);
    await authBox.put('role', response['role']);

    return AuthUser(
      id: '',
      email: email,
      fullName: fullName,
      role: response['role'],
      onboardingComplete: false,
    );
  }

  Future<bool> _refreshToken() async {
    try {
      final refreshToken = await storage.read(key: 'refresh_token');
      if (refreshToken == null) return false;

      final response = await apiClient.post('/api/v1/auth/refresh', body: {
        'refresh_token': refreshToken,
      });

      await apiClient.setTokens(response['access_token'], response['refresh_token']);
      return true;
    } catch (e) {
      return false;
    }
  }

  Future<void> logout() async {
    await apiClient.clearTokens();
    await authBox.clear();
  }

  Future<bool> isLoggedIn() async {
    final token = await storage.read(key: 'access_token');
    return token != null;
  }
}
