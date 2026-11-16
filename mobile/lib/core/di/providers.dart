import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:hive_flutter/hive_flutter.dart';

import '../../shared/services/api_client.dart';
import '../config/api_config.dart';
import '../../shared/services/auth_service.dart';
import '../../shared/services/offline_service.dart';

// ── Core ───────────────────────────────────────────────────
final secureStorageProvider = Provider<FlutterSecureStorage>((ref) {
  return const FlutterSecureStorage(
    iOptions: IOSOptions(accessibility: KeychainAccessibility.first_unlock),
  );
});

final authBoxProvider = Provider<Box>((ref) => Hive.box('auth'));
final offlineLogsBoxProvider = Provider<Box>((ref) => Hive.box('offline_logs'));
final userPrefsBoxProvider = Provider<Box>((ref) => Hive.box('user_prefs'));

// ── API Client ───────────────────────────────────────────
final apiClientProvider = Provider<ApiClient>((ref) {
  final storage = ref.watch(secureStorageProvider);
  final origin = ref.watch(userPrefsBoxProvider).get('server', defaultValue: ApiConfig.baseUrl) as String;
  final client = ApiClient(storage: storage, baseUrl: origin);
  ref.onDispose(client.close);
  return client;
});

// ── Auth Service ──────────────────────────────────────────
final authServiceProvider = Provider<AuthService>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  final storage = ref.watch(secureStorageProvider);
  final authBox = ref.watch(authBoxProvider);
  return AuthService(apiClient: apiClient, storage: storage, authBox: authBox);
});

// ── Auth State ───────────────────────────────────────────
final authStateProvider = FutureProvider<AuthUser?>((ref) async {
  final authService = ref.watch(authServiceProvider);
  return await authService.getCurrentUser();
});

// ── Offline Service ───────────────────────────────────────
final offlineServiceProvider = Provider<OfflineService>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  final offlineBox = ref.watch(offlineLogsBoxProvider);
  return OfflineService(apiClient: apiClient, offlineBox: offlineBox);
});

// ── Connectivity ──────────────────────────────────────────
final connectivityProvider = StreamProvider<bool>((ref) async* {
  // Simple connectivity check - in production use connectivity_plus
  yield true;
  await Future.delayed(const Duration(seconds: 5));
});

// Each patient's view must re-fetch when another account signs in on this device.
ApiClient watchPatientClient(Ref ref) {
  ref.watch(authStateProvider.select((state) => state.value?.id));
  return ref.watch(apiClientProvider);
}

// ── Patient Profile ───────────────────────────────────────
final patientProfileProvider =
    FutureProvider.autoDispose.family<Map<String, dynamic>?, String>(
        (ref, patientId) async {
  final apiClient = watchPatientClient(ref);
  try {
    return await apiClient.get('/api/v1/patients/me');
  } catch (e) {
    return null;
  }
});

// ── Daily Logs ────────────────────────────────────────────
final dailyLogsProvider =
    FutureProvider.autoDispose.family<List<Map<String, dynamic>>, int>((ref, days) async {
  final apiClient = watchPatientClient(ref);
  final response = await apiClient.get('/api/v1/logs/daily?days=$days');
  return List<Map<String, dynamic>>.from(response ?? []);
});

final todayLogProvider = FutureProvider.autoDispose<Map<String, dynamic>?>((ref) async {
  final apiClient = watchPatientClient(ref);
  try {
    return await apiClient.get('/api/v1/logs/daily/today');
  } catch (e) {
    return null;
  }
});

// ── Prescriptions ─────────────────────────────────────────
final prescriptionsProvider =
    FutureProvider.autoDispose<List<Map<String, dynamic>>>((ref) async {
  final apiClient = watchPatientClient(ref);
  final response = await apiClient.medicines();
  return List<Map<String, dynamic>>.from(response ?? []);
});

// ── Reminders ─────────────────────────────────────────────
final remindersProvider =
    FutureProvider.autoDispose<List<Map<String, dynamic>>>((ref) async {
  final apiClient = watchPatientClient(ref);
  final response = await apiClient.get('/api/v1/reminders/');
  return List<Map<String, dynamic>>.from(response ?? []);
});

// ── Trends ────────────────────────────────────────────────
final trendsProvider =
    FutureProvider.autoDispose.family<Map<String, dynamic>, (String, int)>(
        (ref, metric) async {
  final apiClient = watchPatientClient(ref);
  return await apiClient.get('/api/v1/logs/trends/${metric.$1}',
      queryParams: {'days': metric.$2.toString()});
});

// ── Food Logs ─────────────────────────────────────────────
final todayFoodLogsProvider =
    FutureProvider.autoDispose<List<Map<String, dynamic>>>((ref) async {
  final apiClient = watchPatientClient(ref);
  final response = await apiClient.get('/api/v1/food/log/today');
  return List<Map<String, dynamic>>.from(response ?? []);
});
