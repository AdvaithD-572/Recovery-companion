import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:recovery_companion/features/care/care_page.dart';

void main() {
  testWidgets('Reopening or refreshing Records fetches current clinic visits',
      (tester) async {
    var note = 'First checkup';
    final visible = ValueNotifier(true);
    addTearDown(visible.dispose);
    await tester.pumpWidget(ProviderScope(
        overrides: [
          careProvider.overrideWith((ref) async => {
                'clinic': 'Demo clinic',
                'instructions': [],
                'events': [],
                'visits': [
                  {'note': note, 'at': '2026-11-16'}
                ]
              })
        ],
        child: MaterialApp(
            home: ValueListenableBuilder<bool>(
                valueListenable: visible,
                builder: (_, open, __) =>
                    open ? const CarePage() : const SizedBox()))));
    await tester.pumpAndSettle();
    visible.value = false;
    await tester.pumpAndSettle();
    note = 'New clinic visit';
    visible.value = true;
    await tester.pumpAndSettle();
    await tester.scrollUntilVisible(find.text(note), 200,
        scrollable: find.byType(Scrollable).first);
    note = 'Another clinic visit';
    await tester.tap(find.byTooltip('Refresh care record'));
    await tester.pumpAndSettle();
    await tester.scrollUntilVisible(find.text(note), 200,
        scrollable: find.byType(Scrollable).first);
    expect(find.text(note), findsOneWidget);
  });

  testWidgets('Patient reads the completed clinic checkup', (tester) async {
    await tester.pumpWidget(ProviderScope(overrides: [
      careProvider.overrideWith((ref) async => {
            'clinic': 'Demo clinic',
            'instructions': [],
            'events': [],
            'visits': [
              {'note': 'Follow-up recorded', 'at': '2026-11-08'}
            ]
          })
    ], child: const MaterialApp(home: CarePage())));
    await tester.pumpAndSettle();
    await tester.scrollUntilVisible(find.text('Follow-up recorded'), 200,
        scrollable: find.byType(Scrollable).first);
    expect(find.text('Follow-up recorded'), findsOneWidget);
    expect(find.text('Finalize checkup'), findsNothing);
  });
}
