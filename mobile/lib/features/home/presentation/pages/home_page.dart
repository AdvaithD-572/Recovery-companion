import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../../core/theme/app_theme.dart';
import '../../../../core/di/providers.dart';

final diarySyncProvider = StreamProvider.autoDispose<int>((ref) async* {
  final api = watchPatientClient(ref);
  while (true) {
    yield await api.syncDiary();
    await Future<void>.delayed(const Duration(seconds: 30));
  }
});

class HomePage extends ConsumerWidget {
  const HomePage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final patientAsync = ref.watch(patientProfileProvider(''));
    final todayLogAsync = ref.watch(todayLogProvider);
    final prescriptionsAsync = ref.watch(prescriptionsProvider);

    return Scaffold(
      body: SafeArea(
        child: RefreshIndicator(
          onRefresh: () async {
            ref.invalidate(patientProfileProvider(''));
            ref.invalidate(todayLogProvider);
            ref.invalidate(prescriptionsProvider);
          },
          child: CustomScrollView(
            slivers: [
              // App Bar
              SliverToBoxAdapter(
                child: Padding(
                  padding: const EdgeInsets.all(24),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text('Hello!',
                                  style: AppTextStyles.heading(size: 28)),
                              patientAsync.when(
                                data: (patient) => patient != null
                                    ? Text(
                                        'Day ${patient['recovery_day'] ?? 1} of recovery',
                                        style: AppTextStyles.body(
                                            color: AppColors.textMid))
                                    : const SizedBox(),
                                loading: () => const SizedBox(),
                                error: (_, __) => const SizedBox(),
                              ),
                            ],
                          ),
                          GestureDetector(
                            onTap: () => context.push('/profile'),
                            child: Container(
                              width: 48,
                              height: 48,
                              decoration: BoxDecoration(
                                color: AppColors.sagePale,
                                borderRadius: BorderRadius.circular(16),
                              ),
                              child: const Icon(Icons.person_outline,
                                  semanticLabel: 'Profile',
                                  color: AppColors.sage),
                            ),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
              ),

              if ((ref.watch(diarySyncProvider).value ?? 0) > 0)
                SliverToBoxAdapter(
                    child: ListTile(
                        title: Text(
                            '${ref.watch(diarySyncProvider).value} entries pending sync'),
                        trailing: TextButton(
                            onPressed: () => ref.invalidate(diarySyncProvider),
                            child: const Text('Retry')))),
              // Daily Check-in Card
              SliverToBoxAdapter(
                child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 24),
                  child: _buildCheckInCard(context, ref, todayLogAsync),
                ),
              ),

              const SliverToBoxAdapter(child: SizedBox(height: 16)),

              SliverToBoxAdapter(
                  child: Padding(
                      padding: const EdgeInsets.symmetric(horizontal: 24),
                      child: OutlinedButton.icon(
                          icon: const Icon(Icons.medical_information_outlined),
                          label:
                              const Text('Care record and attention tracker'),
                          onPressed: () => context.push('/care')))),
              // Quick Actions
              SliverToBoxAdapter(
                child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 24),
                  child: _buildQuickActions(context),
                ),
              ),

              const SliverToBoxAdapter(child: SizedBox(height: 24)),

              // Today's Medicines
              SliverToBoxAdapter(
                child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 24),
                  child: _buildMedicinesCard(context, prescriptionsAsync),
                ),
              ),

              const SliverToBoxAdapter(child: SizedBox(height: 24)),

              // Food Log
              SliverToBoxAdapter(
                child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 24),
                  child: _buildFoodCard(context, ref),
                ),
              ),

              const SliverToBoxAdapter(child: SizedBox(height: 100)),
            ],
          ),
        ),
      ),
      floatingActionButton: FloatingActionButton(
        tooltip: 'Voice check-in',
        onPressed: () => context.push('/voice'),
        backgroundColor: AppColors.sage,
        child: const Icon(Icons.mic, color: Colors.white),
      ),
    );
  }

  Widget _buildCheckInCard(
      BuildContext context, WidgetRef ref, AsyncValue todayLogAsync) {
    final isCompleted = todayLogAsync.maybeWhen(
      data: (log) => log != null,
      orElse: () => false,
    );

    return GestureDetector(
      onTap: () => context.push('/checkin'),
      child: Container(
        padding: const EdgeInsets.all(20),
        decoration: BoxDecoration(
          gradient: LinearGradient(
            colors: isCompleted
                ? [AppColors.sage, AppColors.sage.withGreen(180)]
                : [AppColors.warmWhite, AppColors.cream],
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
          ),
          borderRadius: BorderRadius.circular(24),
          border: Border.all(
            color: isCompleted ? Colors.transparent : AppColors.sagePale,
            width: 1.5,
          ),
        ),
        child: Row(
          children: [
            Container(
              width: 56,
              height: 56,
              decoration: BoxDecoration(
                color: isCompleted
                    ? Colors.white.withValues(alpha: 0.2)
                    : AppColors.sagePale,
                borderRadius: BorderRadius.circular(16),
              ),
              child: Icon(
                isCompleted ? Icons.check_circle : Icons.edit_note,
                color: isCompleted ? Colors.white : AppColors.sage,
                size: 28,
              ),
            ),
            const SizedBox(width: 16),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    isCompleted ? 'Check-in complete!' : 'Daily check-in',
                    style: AppTextStyles.body(
                        weight: FontWeight.w600,
                        color: isCompleted ? Colors.white : AppColors.textDark),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    isCompleted
                        ? 'Great job! See you tomorrow'
                        : 'How are you feeling today?',
                    style: AppTextStyles.caption(
                        color: isCompleted
                            ? Colors.white.withValues(alpha: 0.8)
                            : AppColors.textMid),
                  ),
                ],
              ),
            ),
            Icon(Icons.arrow_forward_ios,
                size: 16,
                color: isCompleted ? Colors.white : AppColors.textLight),
          ],
        ),
      ),
    );
  }

  Widget _buildQuickActions(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text('Quick actions', style: AppTextStyles.label()),
        const SizedBox(height: 12),
        Row(
          children: [
            _buildActionButton(
                icon: Icons.medication_outlined,
                label: 'Medicines',
                onTap: () => context.push('/prescription')),
            const SizedBox(width: 12),
            _buildActionButton(
                icon: Icons.restaurant_outlined,
                label: 'Food',
                onTap: () => context.push('/food')),
            const SizedBox(width: 12),
            _buildActionButton(
                icon: Icons.insights_outlined,
                label: 'Trends',
                onTap: () => context.push('/trends/pain')),
            const SizedBox(width: 12),
            _buildActionButton(
                icon: Icons.notifications_outlined,
                label: 'Reminders',
                onTap: () => context.push('/reminders')),
          ],
        ),
      ],
    );
  }

  Widget _buildActionButton(
      {required IconData icon,
      required String label,
      required VoidCallback onTap}) {
    return Expanded(
      child: GestureDetector(
        onTap: onTap,
        child: Container(
          padding: const EdgeInsets.symmetric(vertical: 16),
          decoration: BoxDecoration(
              color: AppColors.cream, borderRadius: BorderRadius.circular(16)),
          child: Column(
            children: [
              Icon(icon, color: AppColors.sage, size: 24),
              const SizedBox(height: 8),
              Text(label, style: AppTextStyles.caption()),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildMedicinesCard(
      BuildContext context, AsyncValue prescriptionsAsync) {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(24),
        boxShadow: [
          BoxShadow(
              color: Colors.black.withValues(alpha: 0.04),
              blurRadius: 20,
              offset: const Offset(0, 4))
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text("Today's medicines",
                  style: AppTextStyles.body(weight: FontWeight.w600)),
              TextButton(
                  onPressed: () => context.push('/prescription'),
                  child: const Text('View all')),
            ],
          ),
          const SizedBox(height: 12),
          prescriptionsAsync.when(
            data: (prescriptions) {
              if (prescriptions.isEmpty) {
                return Padding(
                  padding: const EdgeInsets.symmetric(vertical: 16),
                  child: Center(
                      child: Text('No medicines added yet',
                          style: AppTextStyles.caption())),
                );
              }
              return Column(
                children: prescriptions
                    .take(3)
                    .map<Widget>((rx) => Padding(
                          padding: const EdgeInsets.symmetric(vertical: 8),
                          child: Row(
                            children: [
                              Container(
                                width: 8,
                                height: 8,
                                decoration: BoxDecoration(
                                  color: (rx['is_compulsory'] ?? false)
                                      ? AppColors.sage
                                      : AppColors.blue,
                                  shape: BoxShape.circle,
                                ),
                              ),
                              const SizedBox(width: 12),
                              Expanded(
                                  child: Text(rx['drug_name'] ?? '',
                                      style: AppTextStyles.body())),
                              Text('${rx['doses_remaining']} doses left',
                                  style: AppTextStyles.caption(
                                      color: (rx['needs_refill'] ?? false)
                                          ? AppColors.caution
                                          : AppColors.textLight)),
                            ],
                          ),
                        ))
                    .toList(),
              );
            },
            loading: () => const Center(
                child: Padding(
                    padding: EdgeInsets.all(16),
                    child: CircularProgressIndicator(strokeWidth: 2))),
            error: (_, __) => const Padding(
                padding: EdgeInsets.all(16), child: Text('Failed to load')),
          ),
        ],
      ),
    );
  }

  Widget _buildFoodCard(BuildContext context, WidgetRef ref) {
    final foodLogsAsync = ref.watch(todayFoodLogsProvider);

    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(24),
        boxShadow: [
          BoxShadow(
              color: Colors.black.withValues(alpha: 0.04),
              blurRadius: 20,
              offset: const Offset(0, 4))
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text("Today's meals",
                  style: AppTextStyles.body(weight: FontWeight.w600)),
              TextButton(
                  onPressed: () => context.push('/food'),
                  child: const Text('Log meal')),
            ],
          ),
          const SizedBox(height: 12),
          foodLogsAsync.when(
            data: (logs) {
              if (logs.isEmpty) {
                return Padding(
                  padding: const EdgeInsets.symmetric(vertical: 16),
                  child: Center(
                    child: Column(
                      children: [
                        const Icon(Icons.camera_alt_outlined,
                            color: AppColors.textLight, size: 32),
                        const SizedBox(height: 8),
                        Text('No meals logged today',
                            style: AppTextStyles.caption()),
                      ],
                    ),
                  ),
                );
              }
              return Column(
                children: logs
                    .take(3)
                    .map<Widget>((log) => Padding(
                          padding: const EdgeInsets.symmetric(vertical: 8),
                          child: Row(
                            children: [
                              Container(
                                padding: const EdgeInsets.all(8),
                                decoration: BoxDecoration(
                                    color: AppColors.bluePale,
                                    borderRadius: BorderRadius.circular(8)),
                                child: Icon(_getMealIcon(log['meal_type']),
                                    size: 16, color: AppColors.blue),
                              ),
                              const SizedBox(width: 12),
                              Expanded(
                                child: Text(
                                  (log['food_items'] as List?)
                                          ?.map((i) => i['name'])
                                          .join(', ') ??
                                      '',
                                  style: AppTextStyles.body(),
                                  maxLines: 1,
                                  overflow: TextOverflow.ellipsis,
                                ),
                              ),
                            ],
                          ),
                        ))
                    .toList(),
              );
            },
            loading: () => const Center(
                child: Padding(
                    padding: EdgeInsets.all(16),
                    child: CircularProgressIndicator(strokeWidth: 2))),
            error: (_, __) => const Padding(
                padding: EdgeInsets.all(16), child: Text('Failed to load')),
          ),
        ],
      ),
    );
  }

  IconData _getMealIcon(String? type) {
    switch (type) {
      case 'breakfast':
        return Icons.wb_sunny_outlined;
      case 'lunch':
        return Icons.lunch_dining;
      case 'dinner':
        return Icons.dinner_dining;
      default:
        return Icons.fastfood_outlined;
    }
  }
}
