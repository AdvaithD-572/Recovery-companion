import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:timezone/data/latest.dart' as zones;
import 'package:timezone/timezone.dart' as tz;

class DeviceReminders {
  static final plugin = FlutterLocalNotificationsPlugin();
  static bool initialized = false;
  static Future<bool> prepare() async {
    if (kIsWeb || defaultTargetPlatform != TargetPlatform.android) return false;
    if (!initialized) {
      zones.initializeTimeZones();
      await plugin.initialize(
          settings: const InitializationSettings(
              android: AndroidInitializationSettings('@mipmap/ic_launcher')));
      initialized = true;
    }
    return true;
  }

  static Future<void> clear() async {
    if (await prepare()) await plugin.cancelAll();
  }

  static Future<bool> apply(List<Map<String, dynamic>> rows,
      {bool ask = false}) async {
    if (!await prepare()) return false;
    final android = plugin.resolvePlatformSpecificImplementation<
        AndroidFlutterLocalNotificationsPlugin>()!;
    if (ask) await android.requestNotificationsPermission();
    if (await android.areNotificationsEnabled() != true) return false;
    final zone = await const MethodChannel('recovery/device')
        .invokeMethod<String>('timezone');
    final location = tz.getLocation(zone ?? 'UTC');
    final today = tz.TZDateTime.now(location);
    await plugin.cancelAll();
    var id = 0;
    for (final row in rows.where((r) => r['is_active'] == true)) {
      final clock =
          row['scheduled_time'].toString().split(':').map(int.parse).toList();
      for (final weekday in (row['days_of_week'] as List).cast<int>().toSet()) {
        var offset = (weekday + 1 - today.weekday) % 7;
        var next = tz.TZDateTime(location, today.year, today.month,
            today.day + offset, clock[0], clock[1]);
        if (!next.isAfter(today)) {
          next = tz.TZDateTime(location, next.year, next.month, next.day + 7,
              clock[0], clock[1]);
        }
        await plugin.zonedSchedule(
            id: id++,
            scheduledDate: next,
            title: 'Recovery Companion',
            body: 'Your scheduled recovery reminder is ready.',
            notificationDetails: const NotificationDetails(
                android: AndroidNotificationDetails(
                    'care_schedule', 'Recovery reminders')),
            androidScheduleMode: AndroidScheduleMode.inexactAllowWhileIdle,
            matchDateTimeComponents: DateTimeComponents.dayOfWeekAndTime);
      }
    }
    return true;
  }
}
