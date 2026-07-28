import 'dart:convert';
import 'package:hive_flutter/hive_flutter.dart';

import 'api_client.dart';

class OfflineService {
  final ApiClient apiClient;
  final Box offlineBox;

  OfflineService({
    required this.apiClient,
    required this.offlineBox,
  });

  /// Queue a daily log for later sync when online
  Future<void> queueDailyLog(Map<String, dynamic> logData) async {
    final logs = _getQueuedLogs();
    logs.add({
      ...logData,
      'queued_at': DateTime.now().toIso8601String(),
    });
    await offlineBox.put('pending_daily_logs', jsonEncode(logs));
  }

  /// Queue a dose log for later sync
  Future<void> queueDoseLog(Map<String, dynamic> logData) async {
    final logs = _getQueuedDoseLogs();
    logs.add({
      ...logData,
      'queued_at': DateTime.now().toIso8601String(),
    });
    await offlineBox.put('pending_dose_logs', jsonEncode(logs));
  }

  /// Queue a food log for later sync
  Future<void> queueFoodLog(Map<String, dynamic> logData) async {
    final logs = _getQueuedFoodLogs();
    logs.add({
      ...logData,
      'queued_at': DateTime.now().toIso8601String(),
    });
    await offlineBox.put('pending_food_logs', jsonEncode(logs));
  }

  /// Sync all pending logs to the server
  Future<int> syncPendingLogs() async {
    int synced = 0;

    // Sync daily logs
    final dailyLogs = _getQueuedLogs();
    final successfulDaily = <Map<String, dynamic>>[];
    for (final log in dailyLogs) {
      try {
        await apiClient.post('/api/v1/logs/daily', body: log);
        synced++;
      } catch (e) {
        successfulDaily.add(log);
      }
    }
    await offlineBox.put('pending_daily_logs', jsonEncode(successfulDaily));

    // Sync dose logs
    final doseLogs = _getQueuedDoseLogs();
    final successfulDose = <Map<String, dynamic>>[];
    for (final log in doseLogs) {
      try {
        await apiClient.post('/api/v1/prescriptions/dose-log', body: log);
        synced++;
      } catch (e) {
        successfulDose.add(log);
      }
    }
    await offlineBox.put('pending_dose_logs', jsonEncode(successfulDose));

    // Sync food logs
    final foodLogs = _getQueuedFoodLogs();
    final successfulFood = <Map<String, dynamic>>[];
    for (final log in foodLogs) {
      try {
        await apiClient.post('/api/v1/food/log', body: log);
        synced++;
      } catch (e) {
        successfulFood.add(log);
      }
    }
    await offlineBox.put('pending_food_logs', jsonEncode(successfulFood));

    return synced;
  }

  List<Map<String, dynamic>> _getQueuedLogs() {
    final data = offlineBox.get('pending_daily_logs');
    if (data == null) return [];
    final List<dynamic> decoded = jsonDecode(data);
    return decoded.cast<Map<String, dynamic>>();
  }

  List<Map<String, dynamic>> _getQueuedDoseLogs() {
    final data = offlineBox.get('pending_dose_logs');
    if (data == null) return [];
    final List<dynamic> decoded = jsonDecode(data);
    return decoded.cast<Map<String, dynamic>>();
  }

  List<Map<String, dynamic>> _getQueuedFoodLogs() {
    final data = offlineBox.get('pending_food_logs');
    if (data == null) return [];
    final List<dynamic> decoded = jsonDecode(data);
    return decoded.cast<Map<String, dynamic>>();
  }

  Future<int> getPendingCount() async {
    return _getQueuedLogs().length + 
           _getQueuedDoseLogs().length + 
           _getQueuedFoodLogs().length;
  }
}
