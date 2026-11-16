import '../../../../shared/widgets/medicine_form.dart';
import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
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
              tooltip: 'Scan prescription',
              icon: const Icon(Icons.document_scanner_outlined),
              onPressed: () async {
                try {
                  final photo = await ImagePicker()
                      .pickImage(source: ImageSource.camera, imageQuality: 80);
                  if (photo == null || !context.mounted) return;
                  final api = ref.read(apiClientProvider);
                  final drafts = await api.uploadFile(
                      '/api/v1/prescriptions/scan-ocr',
                      await photo.readAsBytes(),
                      photo.name,
                      'file',
                      mimeType: 'image/jpeg');
                  if (!context.mounted) return;
                  if ((drafts as List).isEmpty) {
                    ScaffoldMessenger.of(context).showSnackBar(const SnackBar(
                        content: Text(
                            'No medicine could be read. Use manual entry.')));
                    return;
                  }
                  for (final draft in drafts) {
                    if (!context.mounted) return;
                    final med = await medicineForm(context,
                        draft: Map<String, dynamic>.from(draft));
                    if (med != null) {
                      await api.post('/api/v1/prescriptions/', body: med);
                    }
                  }
                  ref.invalidate(prescriptionsProvider);
                } catch (e) {
                  if (context.mounted) {
                    ScaffoldMessenger.of(context)
                        .showSnackBar(SnackBar(content: Text(e.toString())));
                  }
                }
              }),
          IconButton(
            tooltip: 'Add medicine',
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

            final compulsory =
                prescriptions.where((p) => p['is_compulsory'] == true).toList();
            final optional = prescriptions
                .where((p) => p['is_compulsory'] == false)
                .toList();

            return ListView(
              padding: const EdgeInsets.all(24),
              children: [
                if (prescriptions.first['_cachedAt'] != null)
                  Text('Offline · showing medicines saved on ${prescriptions.first['_cachedAt'].toString().split('T').first}.'),
                if (compulsory.isNotEmpty) ...[
                  Text('Prescribed medicines', style: AppTextStyles.label()),
                  const SizedBox(height: 12),
                  ...compulsory
                      .map((rx) => _buildPrescriptionCard(context, ref, rx)),
                  const SizedBox(height: 24),
                ],
                if (optional.isNotEmpty) ...[
                  Text('Optional / As needed', style: AppTextStyles.label()),
                  const SizedBox(height: 12),
                  ...optional
                      .map((rx) => _buildPrescriptionCard(context, ref, rx)),
                ],
              ],
            );
          },
          loading: () => const Center(child: CircularProgressIndicator()),
          error: (_, __) =>
              const Center(child: Text('Failed to load prescriptions')),
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
              width: 80,
              height: 80,
              decoration: BoxDecoration(
                color: AppColors.sagePale,
                borderRadius: BorderRadius.circular(24),
              ),
              child: const Icon(Icons.medication_outlined,
                  color: AppColors.sage, size: 40),
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

  Widget _buildPrescriptionCard(
      BuildContext context, WidgetRef ref, Map<String, dynamic> rx) {
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
                width: 40,
                height: 40,
                decoration: BoxDecoration(
                  color: (rx['is_compulsory'] ?? false)
                      ? AppColors.sagePale
                      : AppColors.bluePale,
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Icon(
                  Icons.medication,
                  color: (rx['is_compulsory'] ?? false)
                      ? AppColors.sage
                      : AppColors.blue,
                  size: 20,
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(rx['drug_name'] ?? '',
                        style: AppTextStyles.body(weight: FontWeight.w600)),
                    Text(rx['dosage'] ?? '', style: AppTextStyles.caption()),
                  ],
                ),
              ),
              if (needsRefill)
                Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                  decoration: BoxDecoration(
                    color: AppColors.cautionPale,
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Text('Refill',
                      style: AppTextStyles.caption(color: AppColors.caution)),
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
              value: (rx['doses_remaining'] as int) /
                  (rx['total_doses_bought'] as int).clamp(1, double.infinity),
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

  Future<void> _showAddPrescription(BuildContext context, WidgetRef ref) async {
    final data = await medicineForm(context);
    if (data == null || !context.mounted) return;
    try {
      await ref
          .read(apiClientProvider)
          .post('/api/v1/prescriptions/', body: data);
      ref.invalidate(prescriptionsProvider);
    } catch (e) {
      if (context.mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text(e.toString())));
      }
    }
  }

  Future<void> _showLogDose(
      BuildContext context, WidgetRef ref, Map<String, dynamic> rx) async {
    final now = DateTime.now();
    final times = List<String>.from(rx['frequency']?['times'] ?? []);
    String? selected = times.isEmpty ? null : times.first;
    bool taken = true;
    String reason = '';
    final result = await showDialog<bool>(
        context: context,
        builder: (ctx) => StatefulBuilder(
            builder: (ctx, update) => AlertDialog(
                    title: Text(rx['drug_name']),
                    content: SingleChildScrollView(
                        child:
                            Column(mainAxisSize: MainAxisSize.min, children: [
                      Text(rx['dosage']),
                      if (times.isNotEmpty)
                        DropdownButton<String>(
                            isExpanded: true,
                            value: selected,
                            items: times
                                .map((t) => DropdownMenuItem(
                                    value: t, child: Text("Today · $t")))
                                .toList(),
                            onChanged: (v) => update(() => selected = v)),
                      SegmentedButton<bool>(
                          segments: const [
                            ButtonSegment(value: true, label: Text('Taken')),
                            ButtonSegment(value: false, label: Text('Skipped'))
                          ],
                          selected: {
                            taken
                          },
                          onSelectionChanged: (s) =>
                              update(() => taken = s.first)),
                      if (!taken)
                        TextField(
                            maxLength: 200,
                            decoration: const InputDecoration(
                                labelText: 'Reason (optional)'),
                            onChanged: (v) => reason = v)
                    ])),
                    actions: [
                      TextButton(
                          onPressed: () => Navigator.pop(ctx, false),
                          child: const Text('Cancel')),
                      FilledButton(
                          onPressed: () => Navigator.pop(ctx, true),
                          child: const Text('Record'))
                    ])));
    if (result != true || !context.mounted) return;
    final parts = selected?.split(':');
    final scheduled = parts == null
        ? now
        : DateTime(now.year, now.month, now.day, int.parse(parts[0]),
            int.parse(parts[1]));
    try {
      final response = await ref
          .read(apiClientProvider)
          .post('/api/v1/prescriptions/dose-log', body: {
        'prescription_id': rx['id'],
        'scheduled_time': scheduled.toUtc().toIso8601String(),
        'taken': taken,
        'skip_reason': taken ? null : reason
      });
      ref.invalidate(prescriptionsProvider);
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(
            content: Text(response['queued'] == true
                ? 'Saved on this device · Pending sync'
                : 'Dose recorded')));
      }
    } catch (e) {
      if (context.mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text(e.toString())));
      }
    }
  }
}
