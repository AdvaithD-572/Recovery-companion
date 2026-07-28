import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/theme/app_theme.dart';
import '../../../../core/di/providers.dart';

class PrescriptionPage extends ConsumerWidget {
  const PrescriptionPage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final prescriptionsAsync = ref.watch(prescriptionsProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('My Medicines'),
        actions: [
          IconButton(
            icon: const Icon(Icons.add),
            onPressed: () => _showAddPrescription(context, ref),
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: () async => ref.invalidate(prescriptionsProvider),
        child: prescriptionsAsync.when(
          data: (prescriptions) {
            if (prescriptions.isEmpty) {
              return _buildEmptyState(context, ref);
            }
            
            final compulsory = prescriptions.where((p) => p['is_compulsory'] == true).toList();
            final optional = prescriptions.where((p) => p['is_compulsory'] == false).toList();

            return ListView(
              padding: const EdgeInsets.all(24),
              children: [
                if (compulsory.isNotEmpty) ...[
                  Text('Prescribed medicines', style: AppTextStyles.label()),
                  const SizedBox(height: 12),
                  ...compulsory.map((rx) => _buildPrescriptionCard(context, ref, rx)),
                  const SizedBox(height: 24),
                ],
                if (optional.isNotEmpty) ...[
                  Text('Optional / As needed', style: AppTextStyles.label()),
                  const SizedBox(height: 12),
                  ...optional.map((rx) => _buildPrescriptionCard(context, ref, rx)),
                ],
              ],
            );
          },
          loading: () => const Center(child: CircularProgressIndicator()),
          error: (_, __) => const Center(child: Text('Failed to load prescriptions')),
        ),
      ),
    );
  }

  Widget _buildEmptyState(BuildContext context, WidgetRef ref) {
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
              child: const Icon(Icons.medication_outlined, color: AppColors.sage, size: 40),
            ),
            const SizedBox(height: 24),
            Text('No medicines yet', style: AppTextStyles.heading()),
            const SizedBox(height: 8),
            Text(
              'Add your prescriptions to track doses and get reminders.',
              style: AppTextStyles.body(color: AppColors.textMid),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 24),
            ElevatedButton.icon(
              onPressed: () => _showAddPrescription(context, ref),
              icon: const Icon(Icons.add),
              label: const Text('Add medicine'),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildPrescriptionCard(BuildContext context, WidgetRef ref, Map<String, dynamic> rx) {
    final needsRefill = rx['needs_refill'] ?? false;
    
    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: needsRefill ? AppColors.caution : Colors.transparent,
          width: needsRefill ? 1.5 : 0,
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                width: 40, height: 40,
                decoration: BoxDecoration(
                  color: (rx['is_compulsory'] ?? false) ? AppColors.sagePale : AppColors.bluePale,
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Icon(
                  Icons.medication,
                  color: (rx['is_compulsory'] ?? false) ? AppColors.sage : AppColors.blue,
                  size: 20,
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(rx['drug_name'] ?? '', style: AppTextStyles.body(weight: FontWeight.w600)),
                    Text(rx['dosage'] ?? '', style: AppTextStyles.caption()),
                  ],
                ),
              ),
              if (needsRefill)
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                  decoration: BoxDecoration(
                    color: AppColors.cautionPale,
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Text('Refill', style: AppTextStyles.caption(color: AppColors.caution)),
                ),
            ],
          ),
          const SizedBox(height: 16),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                '${rx['doses_remaining']} doses remaining',
                style: AppTextStyles.body(color: AppColors.textMid),
              ),
              TextButton(
                onPressed: () => _showLogDose(context, ref, rx),
                child: const Text('Log dose'),
              ),
            ],
          ),
          // Progress bar
          ClipRRect(
            borderRadius: BorderRadius.circular(4),
            child: LinearProgressIndicator(
              value: (rx['doses_remaining'] as int) / (rx['total_doses_bought'] as int).clamp(1, double.infinity),
              backgroundColor: AppColors.cream,
              valueColor: AlwaysStoppedAnimation<Color>(
                needsRefill ? AppColors.caution : AppColors.sage,
              ),
              minHeight: 6,
            ),
          ),
        ],
      ),
    );
  }

  void _showAddPrescription(BuildContext context, WidgetRef ref) {
    final nameController = TextEditingController();
    final dosageController = TextEditingController();
    int totalDoses = 30;

    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (context) => Container(
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
              Text('Add medicine', style: AppTextStyles.heading()),
              const SizedBox(height: 24),
              TextField(
                controller: nameController,
                decoration: const InputDecoration(labelText: 'Medicine name'),
              ),
              const SizedBox(height: 16),
              TextField(
                controller: dosageController,
                decoration: const InputDecoration(labelText: 'Dosage (e.g., 500mg)'),
              ),
              const SizedBox(height: 16),
              Text('Total doses', style: AppTextStyles.label()),
              Slider(
                value: totalDoses.toDouble(),
                min: 7, max: 90,
                divisions: 83,
                label: '$totalDoses',
                onChanged: (v) => totalDoses = v.round(),
              ),
              const SizedBox(height: 24),
              SizedBox(
                width: double.infinity,
                child: ElevatedButton(
                  onPressed: () async {
                    try {
                      final apiClient = ref.read(apiClientProvider);
                      await apiClient.post('/api/v1/prescriptions/', body: {
                        'drug_name': nameController.text,
                        'dosage': dosageController.text,
                        'frequency': {'times': ['08:00', '20:00']},
                        'is_compulsory': true,
                        'total_doses_bought': totalDoses,
                        'start_date': DateTime.now().toIso8601String().split('T')[0],
                      });
                      ref.invalidate(prescriptionsProvider);
                      if (context.mounted) Navigator.pop(context);
                    } catch (e) {
                      if (context.mounted) {
                        ScaffoldMessenger.of(context).showSnackBar(
                          SnackBar(content: Text('Error: $e')),
                        );
                      }
                    }
                  },
                  child: const Text('Add'),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  void _showLogDose(BuildContext context, WidgetRef ref, Map<String, dynamic> rx) {
    showModalBottomSheet(
      context: context,
      backgroundColor: Colors.transparent,
      builder: (context) => Container(
        padding: const EdgeInsets.all(24),
        decoration: const BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text('Log dose', style: AppTextStyles.heading()),
            const SizedBox(height: 8),
            Text('${rx['drug_name']} - ${rx['dosage']}', style: AppTextStyles.body(color: AppColors.textMid)),
            const SizedBox(height: 24),
            Row(
              children: [
                Expanded(
                  child: OutlinedButton(
                    onPressed: () async {
                      try {
                        final apiClient = ref.read(apiClientProvider);
                        await apiClient.post('/api/v1/prescriptions/dose-log', body: {
                          'prescription_id': rx['id'],
                          'scheduled_time': DateTime.now().toIso8601String(),
                          'taken': false,
                        });
                        ref.invalidate(prescriptionsProvider);
                        if (context.mounted) Navigator.pop(context);
                      } catch (e) {
                        if (context.mounted) {
                          ScaffoldMessenger.of(context).showSnackBar(
                            SnackBar(content: Text('Error: $e')),
                          );
                        }
                      }
                    },
                    child: const Text('Missed'),
                  ),
                ),
                const SizedBox(width: 16),
                Expanded(
                  child: ElevatedButton(
                    onPressed: () async {
                      try {
                        final apiClient = ref.read(apiClientProvider);
                        await apiClient.post('/api/v1/prescriptions/dose-log', body: {
                          'prescription_id': rx['id'],
                          'scheduled_time': DateTime.now().toIso8601String(),
                          'taken': true,
                        });
                        ref.invalidate(prescriptionsProvider);
                        if (context.mounted) Navigator.pop(context);
                      } catch (e) {
                        if (context.mounted) {
                          ScaffoldMessenger.of(context).showSnackBar(
                            SnackBar(content: Text('Error: $e')),
                          );
                        }
                      }
                    },
                    child: const Text('Taken'),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
