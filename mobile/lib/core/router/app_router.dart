import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../features/onboarding/presentation/pages/onboarding_page.dart';
import '../../features/home/presentation/pages/home_page.dart';
import '../../features/questionnaire/presentation/pages/questionnaire_page.dart';
import '../../features/prescription/presentation/pages/prescription_page.dart';
import '../../features/food_log/presentation/pages/food_log_page.dart';
import '../../features/trends/presentation/pages/trends_page.dart';
import '../../features/voice_bot/presentation/pages/voice_session_page.dart';
import '../../features/reminders/presentation/pages/reminders_page.dart';
import '../../features/login/presentation/pages/login_page.dart';
import '../../features/profile/presentation/pages/profile_page.dart';
import '../di/providers.dart';
import '../../features/care/care_page.dart';

final appRouterProvider = Provider<GoRouter>((ref) {
  final authState = ref.watch(authStateProvider);

  return GoRouter(
    initialLocation: '/home',
    redirect: (context, state) {
      final isLoggedIn = authState.maybeWhen(
        data: (auth) => auth != null,
        orElse: () => false,
      );
      final onboarded = authState.maybeWhen(
        data: (auth) => auth?.onboardingComplete ?? false,
        orElse: () => false,
      );

      if (!isLoggedIn) {
        return state.matchedLocation == '/login' ? null : '/login';
      }
      if (onboarded &&
          (state.matchedLocation == '/login' ||
              state.matchedLocation == '/onboarding')) {
        return '/home';
      }
      if (isLoggedIn &&
          !onboarded &&
          !state.matchedLocation.startsWith('/onboarding')) {
        return '/onboarding';
      }
      return null;
    },
    routes: [
      GoRoute(path: '/login', builder: (_, __) => const LoginPage()),
      GoRoute(path: '/onboarding', builder: (_, __) => const OnboardingPage()),
      ShellRoute(
          builder: (context, state, child) {
            const paths = [
              '/home',
              '/prescription',
              '/food',
              '/trends/pain',
              '/care'
            ];
            final path = state.uri.path;
            final index = path.startsWith('/trends') ? 3 : paths.indexOf(path);
            return Scaffold(
                body: child,
                bottomNavigationBar: index < 0
                    ? null
                    : NavigationBar(
                        selectedIndex: index,
                        onDestinationSelected: (i) => context.go(paths[i]),
                        destinations: const [
                            NavigationDestination(
                                icon: Icon(Icons.today_outlined),
                                label: 'Today'),
                            NavigationDestination(
                                icon: Icon(Icons.medication_outlined),
                                label: 'Medicines'),
                            NavigationDestination(
                                icon: Icon(Icons.restaurant_outlined),
                                label: 'Food'),
                            NavigationDestination(
                                icon: Icon(Icons.insights), label: 'Progress'),
                            NavigationDestination(
                                icon: Icon(Icons.folder_outlined),
                                label: 'Records')
                          ]));
          },
          routes: [
            GoRoute(path: '/home', builder: (_, __) => const HomePage()),
            GoRoute(
                path: '/checkin',
                builder: (_, __) => const QuestionnairePage()),
            GoRoute(
                path: '/prescription',
                builder: (_, __) => const PrescriptionPage()),
            GoRoute(path: '/food', builder: (_, __) => const FoodLogPage()),
            GoRoute(
                path: '/trends/:metric',
                builder: (context, state) =>
                    TrendsPage(metric: state.pathParameters['metric']!)),
            GoRoute(
                path: '/voice', builder: (_, __) => const VoiceSessionPage()),
            GoRoute(
                path: '/reminders', builder: (_, __) => const RemindersPage()),
            GoRoute(path: '/care', builder: (_, __) => const CarePage()),
          ]),
      GoRoute(path: '/profile', builder: (_, __) => const ProfilePage()),
    ],
  );
});
