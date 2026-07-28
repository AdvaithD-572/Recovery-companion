import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/theme/app_theme.dart';
import '../../../../core/di/providers.dart';

class RemindersPage extends ConsumerStatefulWidget {
  const RemindersPage({super.key});

  @override
  ConsumerState<RemindersPage> createState() => _RemindersPageState();
}

class _RemindersPageState extends ConsumerState<RemindersPage> {
  List<Map<String, dynamic>> _reminders = [];
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _loadReminders();
  }

  Future<void> _loadReminders() async {
    try {
      final apiClient = ref.read(apiClientProvider);
      final response = await apiClient.get('/api/v1/reminders/');
      setState(() {
        _reminders = List<Map<String, dynamic>>.from(response ?? []);
        _isLoading = false;
      });
    } catch (e) {
      setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Reminders'),
        actions: [
          IconButton(
            icon: const Icon(Icons.add),
            onPressed: _showAddReminder,
          ),
        ],
      ),
      body: _isLoading
        ? const Center(child: CircularProgressIndicator())
        : _reminders.isEmpty
          ? _buildEmptyState()
          : _buildRemindersList(),
    );
  }

  Widget _buildEmptyState() {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Container(
              width: 80, height: 80,
              decoration: BoxDecoration(
                color: AppColors.sagePale,
                borderRadius: BorderRadius.circular(24),
              ),
              child: const Icon(Icons.notifications_outlined, color: AppColors.sage, size: 40),
            ),
            const SizedBox(height: 24),
            Text('No reminders yet', style: AppTextStyles.heading()),
            const SizedBox(height: 8),
            Text(
              'Set up reminders for medicines, water, and more.',
              style: AppTextStyles.body(color: AppColors.textMid),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 24),
            ElevatedButton.icon(
              onPressed: _showAddReminder,
              icon: const Icon(Icons.add),
              label: const Text('Add reminder'),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildRemindersList() {
    return ListView(
      padding: const EdgeInsets.all(24),
      children: [
        // Group by type
        ..._buildReminderGroup('Medicines', 'medicine'),
        ..._buildReminderGroup('Water', 'water'),
        ..._buildReminderGroup('Meals', 'meal'),
        ..._buildReminderGroup('Exercise', 'exercise'),
        ..._buildReminderGroup('Daily check-in', 'checkin'),
        ..._buildReminderGroup('Refill', 'refill'),
      ],
    );
  }

  List<Widget> _buildReminderGroup(String title, String type) {
    final reminders = _reminders.where((r) => r['reminder_type'] == type).toList();
    if (reminders.isEmpty) return [];

    return [
      Text(title, style: AppTextStyles.label()),
      const SizedBox(height: 12),
      ...reminders.map((r) => _buildReminderCard(r)),
      const SizedBox(height: 16),
    ];
  }

  Widget _buildReminderCard(Map<String, dynamic> reminder) {
    final isActive = reminder['is_active'] ?? true;
    final scheduledTime = reminder['scheduled_time'] ?? '';
    final days = reminder['days_of_week'] as List? ?? [];

    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16),
      ),
      child: Row(
        children: [
          Container(
            width: 48, height: 48,
            decoration: BoxDecoration(
              color: isActive ? AppColors.sagePale : AppColors.cream,
              borderRadius: BorderRadius.circular(12),
            ),
            child: Icon(
              _getReminderIcon(reminder['reminder_type']),
              color: isActive ? AppColors.sage : AppColors.textLight,
            ),
          ),
          const SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  scheduledTime.isNotEmpty ? _formatTime(scheduledTime) : 'Not set',
                  style: AppTextStyles.body(weight: FontWeight.w600),
                ),
                Text(
                  _formatDays(days),
                  style: AppTextStyles.caption(),
                ),
              ],
            ),
          ),
          Switch(
            value: isActive,
            onChanged: (value) => _toggleReminder(reminder['id'], value),
            activeThumbColor: AppColors.sage,
          ),
        ],
      ),
    );
  }

  IconData _getReminderIcon(String? type) {
    switch (type) {
      case 'medicine': return Icons.medication;
      case 'water': return Icons.water_drop;
      case 'meal': return Icons.restaurant;
      case 'exercise': return Icons.directions_run;
      case 'checkin': return Icons.edit_note;
      case 'refill': return Icons.refresh;
      default: return Icons.notifications;
    }
  }

  String _formatTime(String time) {
    try {
      final parts = time.split(':');
      final hour = int.parse(parts[0]);
      final minute = parts[1];
      final period = hour >= 12 ? 'PM' : 'AM';
      final displayHour = hour > 12 ? hour - 12 : (hour == 0 ? 12 : hour);
      return '$displayHour:$minute $period';
    } catch (e) {
      return time;
    }
  }

  String _formatDays(List days) {
    if (days.isEmpty) return 'Not set';
    if (days.length == 7) return 'Every day';
    
    final dayNames = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
    return days.map((d) => dayNames[d as int]).join(', ');
  }

  void _showAddReminder() {
    String selectedType = 'medicine';
    TimeOfDay selectedTime = const TimeOfDay(hour: 9, minute: 0);
    List<int> selectedDays = [0, 1, 2, 3, 4, 5, 6];

    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (context) => StatefulBuilder(
        builder: (context, setModalState) => Container(
          padding: EdgeInsets.only(
            bottom: MediaQuery.of(context).viewInsets.bottom,
          ),
          decoration: const BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
          ),
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('Add reminder', style: AppTextStyles.heading()),
                const SizedBox(height: 24),

                // Type selector
                Text('Type', style: AppTextStyles.label()),
                const SizedBox(height: 8),
                Wrap(
                  spacing: 8,
                  children: [
                    {'type': 'medicine', 'label': 'Medicine'},
                    {'type': 'water', 'label': 'Water'},
                    {'type': 'meal', 'label': 'Meal'},
                    {'type': 'exercise', 'label': 'Exercise'},
                    {'type': 'checkin', 'label': 'Check-in'},
                  ].map((item) => ChoiceChip(
                    label: Text(item['label']!),
                    selected: selectedType == item['type'],
                    onSelected: (_) => setModalState(() => selectedType = item['type']!),
                    selectedColor: AppColors.sagePale,
                  )).toList(),
                ),
                const SizedBox(height: 24),

                // Time selector
                Text('Time', style: AppTextStyles.label()),
                const SizedBox(height: 8),
                InkWell(
                  onTap: () async {
                    final time = await showTimePicker(
                      context: context,
                      initialTime: selectedTime,
                    );
                    if (time != null) {
                      setModalState(() => selectedTime = time);
                    }
                  },
                  child: Container(
                    padding: const EdgeInsets.all(16),
                    decoration: BoxDecoration(
                      color: AppColors.cream,
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Text(selectedTime.format(context), style: AppTextStyles.body()),
                        const Icon(Icons.access_time, color: AppColors.textMid),
                      ],
                    ),
                  ),
                ),
                const SizedBox(height: 24),

                // Days selector
                Text('Repeat', style: AppTextStyles.label()),
                const SizedBox(height: 8),
                Wrap(
                  spacing: 8,
                  children: ['M', 'T', 'W', 'T', 'F', 'S', 'S'].asMap().entries.map((entry) => FilterChip(
                    label: Text(entry.value),
                    selected: selectedDays.contains(entry.key),
                    onSelected: (selected) {
                      setModalState(() {
                        if (selected) {
                          selectedDays.add(entry.key);
                        } else {
                          selectedDays.remove(entry.key);
                        }
                      });
                    },
                    selectedColor: AppColors.sagePale,
                  )).toList(),
                ),
                const SizedBox(height: 24),

                SizedBox(
                  width: double.infinity,
                  child: ElevatedButton(
                    onPressed: () async {
                      try {
                        final apiClient = ref.read(apiClientProvider);
                        await apiClient.post('/api/v1/reminders/', body: {
                          'reminder_type': selectedType,
                          'scheduled_time': '${selectedTime.hour.toString().padLeft(2, '0')}:${selectedTime.minute.toString().padLeft(2, '0')}',
                          'days_of_week': selectedDays,
                          'is_active': true,
                        });
                        _loadReminders();
                        if (context.mounted) Navigator.pop(context);
                      } catch (e) {
                        if (context.mounted) {
                          ScaffoldMessenger.of(context).showSnackBar(
                            SnackBar(content: Text('Error: $e')),
                          );
                        }
                      }
                    },
                    child: const Text('Add reminder'),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Future<void> _toggleReminder(String id, bool isActive) async {
    try {
      final apiClient = ref.read(apiClientProvider);
      await apiClient.patch('/api/v1/reminders/$id', body: {'is_active': isActive});
      _loadReminders();
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error: $e')),
        );
      }
    }
  }
}
