import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../../core/theme/app_theme.dart';
import '../../../../core/di/providers.dart';

class ProfilePage extends ConsumerWidget {
  const ProfilePage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final patientAsync = ref.watch(patientProfileProvider(''));

    return Scaffold(
      backgroundColor: AppColors.warmWhite,
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
        leading: IconButton(
          icon: const Icon(Icons.arrow_back_ios, color: AppColors.textDark),
          onPressed: () => context.pop(),
        ),
        title: Text('Profile', style: AppTextStyles.heading(size: 20)),
      ),
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.all(24),
          children: [
            // Avatar
            Center(
              child: Container(
                width: 88, height: 88,
                decoration: BoxDecoration(
                  color: AppColors.sagePale,
                  shape: BoxShape.circle,
                ),
                child: const Icon(Icons.person, color: AppColors.sage, size: 44),
              ),
            ),
            const SizedBox(height: 16),

            // Name + Recovery Day
            patientAsync.when(
              data: (patient) {
                if (patient == null) return const SizedBox();
                return Column(
                  children: [
                    Text(
                      patient['full_name'] ?? 'Patient',
                      style: AppTextStyles.heading(size: 22),
                      textAlign: TextAlign.center,
                    ),
                    const SizedBox(height: 4),
                    Text(
                      'Day ${patient['recovery_day'] ?? 1} of recovery',
                      style: AppTextStyles.body(color: AppColors.textMid),
                      textAlign: TextAlign.center,
                    ),
                    const SizedBox(height: 4),
                    if (patient['primary_condition'] != null)
                      Text(
                        patient['primary_condition'],
                        style: AppTextStyles.caption(color: AppColors.textLight),
                        textAlign: TextAlign.center,
                      ),
                  ],
                );
              },
              loading: () => const Center(child: CircularProgressIndicator(strokeWidth: 2)),
              error: (_, __) => const Text('Could not load profile'),
            ),

            const SizedBox(height: 32),

            // Quick nav back to dashboard
            _buildTile(
              icon: Icons.home_outlined,
              label: 'Dashboard',
              onTap: () => context.go('/home'),
            ),
            _buildTile(
              icon: Icons.medication_outlined,
              label: 'My Medicines',
              onTap: () => context.push('/prescription'),
            ),
            _buildTile(
              icon: Icons.restaurant_outlined,
              label: 'Food Log',
              onTap: () => context.push('/food'),
            ),
            _buildTile(
              icon: Icons.insights_outlined,
              label: 'Recovery Trends',
              onTap: () => context.push('/trends/pain'),
            ),

            const SizedBox(height: 24),
            const Divider(),
            const SizedBox(height: 8),

            // Logout
            _buildTile(
              icon: Icons.logout,
              label: 'Log out',
              color: AppColors.caution,
              onTap: () async {
                final apiClient = ref.read(apiClientProvider);
                await apiClient.clearTokens();
                if (context.mounted) context.go('/login');
              },
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildTile({
    required IconData icon,
    required String label,
    required VoidCallback onTap,
    Color? color,
  }) {
    final c = color ?? AppColors.textDark;
    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16),
      ),
      child: ListTile(
        leading: Icon(icon, color: c),
        title: Text(label, style: AppTextStyles.body(color: c)),
        trailing: Icon(Icons.arrow_forward_ios, size: 14, color: c.withAlpha(150)),
        onTap: onTap,
      ),
    );
  }
}
