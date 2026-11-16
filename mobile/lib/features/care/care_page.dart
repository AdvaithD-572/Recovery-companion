import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/di/providers.dart';
import '../../shared/services/api_client.dart';

final careProvider = FutureProvider.autoDispose<Map<String, dynamic>>(
    (ref) async => Map<String, dynamic>.from(
        await watchPatientClient(ref).get('/api/v1/care/me')));

class CarePage extends ConsumerStatefulWidget {
  const CarePage({super.key});
  @override
  ConsumerState<CarePage> createState() => _CarePageState();
}

class _CarePageState extends ConsumerState<CarePage> {
  ApiClient get api => ref.read(apiClientProvider);
  bool busy = false;
  final entry = TextEditingController();
  final instructions = TextEditingController();
  @override
  void dispose() {
    entry.dispose();
    instructions.dispose();
    super.dispose();
  }

  Future<void> addContext(Map event) async {
    var text = '';
    final note = await showDialog<String>(
        context: context,
        builder: (dialog) => AlertDialog(
                title: const Text('Add a correction'),
                content: TextField(
                    maxLines: 3,
                    maxLength: 4000,
                    autofocus: true,
                    decoration: const InputDecoration(
                        labelText: 'What should the clinic know?'),
                    onChanged: (value) => text = value),
                actions: [
                  TextButton(
                      onPressed: () => Navigator.pop(dialog),
                      child: const Text('Cancel')),
                  FilledButton(
                      onPressed: () {
                        if (text.trim().isNotEmpty)
                          Navigator.pop(dialog, text.trim());
                      },
                      child: const Text('Save correction'))
                ]));
    if (note == null || !mounted) return;
    await perform(() async {
      await api.post(
          '/api/v1/care/observations/${event['type']}/${event['id']}/notes',
          body: {'text': note});
    });
  }

  Future<void> perform(Future<void> Function() action) async {
    setState(() => busy = true);
    try {
      await action();
      ref.invalidate(careProvider);
    } catch (error) {
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text(error.toString())));
      }
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
        appBar: AppBar(title: const Text('Care record'), actions: [
          IconButton(
              tooltip: 'Refresh care record',
              icon: const Icon(Icons.refresh),
              onPressed: () => ref.invalidate(careProvider))
        ]),
        body: ref.watch(careProvider).when(
            loading: () => const Center(child: CircularProgressIndicator()),
            error: (e, _) => Center(
                child: TextButton(
                    onPressed: () => ref.invalidate(careProvider),
                    child: const Text('Could not load record · Retry'))),
            data: (data) =>
                ListView(padding: const EdgeInsets.all(20), children: [
                  Text(data['clinic'] ?? 'Connect your clinic',
                      style: Theme.of(context).textTheme.headlineMedium),
                  if (data['clinic'] == null) ...[
                    TextField(
                        controller: entry,
                        decoration: const InputDecoration(
                            labelText: 'Clinic invitation code')),
                    FilledButton(
                        onPressed: busy
                            ? null
                            : () => perform(() async {
                                  final body = {'code': entry.text.trim()};
                                  final preview = await api.post(
                                      '/api/v1/care/invitation/preview',
                                      body: body);
                                  if (!context.mounted) return;
                                  final agree = await showDialog<bool>(
                                      context: context,
                                      builder: (ctx) => AlertDialog(
                                              title: Text(
                                                  'Share with ${preview['clinic']}?'),
                                              content: const Text(
                                                  'Authorized clinic staff will be able to read your recovery diary and print follow-up reports.'),
                                              actions: [
                                                TextButton(
                                                    onPressed: () =>
                                                        Navigator.pop(
                                                            ctx, false),
                                                    child:
                                                        const Text('Cancel')),
                                                FilledButton(
                                                    onPressed: () =>
                                                        Navigator.pop(
                                                            ctx, true),
                                                    child:
                                                        const Text('Connect'))
                                              ]));
                                  if (agree == true) {
                                    await api.post('/api/v1/care/link',
                                        body: body);
                                  }
                                }),
                        child: const Text('Review invitation'))
                  ] else
                    TextButton(
                        onPressed: busy
                            ? null
                            : () => perform(() async {
                                  await api.delete('/api/v1/care/link');
                                }),
                        child: const Text('Disconnect clinic')),
                  const Divider(),
                  Text('Discharge instructions',
                      style: Theme.of(context).textTheme.titleLarge),
                  for (final note in data['instructions'])
                    ListTile(
                        title: Text(note),
                        subtitle: const Text('Patient reported')),
                  TextField(
                      controller: instructions,
                      maxLines: 3,
                      maxLength: 4000,
                      decoration: const InputDecoration(
                          labelText:
                              'Food and care instructions from your doctor')),
                  OutlinedButton(
                      onPressed: busy
                          ? null
                          : () => perform(() async {
                                if (instructions.text.trim().isEmpty) return;
                                await api.post('/api/v1/care/instructions',
                                    body: {'text': instructions.text.trim()});
                                instructions.clear();
                              }),
                      child: const Text('Save instructions')),
                  const Divider(),
                  Text('Attention tracker',
                      style: Theme.of(context).textTheme.titleLarge),
                  _AttentionChart(
                      events: List<Map<String, dynamic>>.from(data['events'])),
                  if ((data['events'] as List).isEmpty)
                    const Text(
                        'Your recorded meals, doses and check-ins appear here.'),
                  for (final e in data['events'])
                    Card(
                        child: ListTile(
                            leading: Icon(e['status'] == 'Critical'
                                ? Icons.priority_high
                                : Icons.history),
                            trailing: e['id'] == null
                                ? null
                                : IconButton(
                                    icon: const Icon(Icons.edit_note),
                                    tooltip: 'Add a correction',
                                    onPressed:
                                        busy ? null : () => addContext(e)),
                            title: Text('${e['type']} · ${e['status']}'),
                            subtitle: Text([
                              "${e['at']}",
                              e['detail'],
                              e['reason']
                            ]
                                .where((v) => v.toString().isNotEmpty)
                                .join('\n')))),
                  const Divider(),
                  Text('Clinic checkups',
                      style: Theme.of(context).textTheme.titleLarge),
                  if ((data['visits'] as List).isEmpty)
                    const Text(
                        'Completed checkups from your clinic appear here.'),
                  for (final v in data['visits'])
                    ListTile(title: Text(v['note']), subtitle: Text(v['at'])),
                ])));
  }
}

class _AttentionChart extends StatelessWidget {
  final List<Map<String, dynamic>> events;
  const _AttentionChart({required this.events});
  @override
  Widget build(BuildContext context) {
    final today = DateUtils.dateOnly(DateTime.now());
    const levels = ['Critical', 'Needs review', 'Unable to assess'];
    const colors = [Color(0xffa73537), Color(0xffa66b14), Color(0xff6d7974)];
    final days = List.generate(7, (i) => today.subtract(Duration(days: 6 - i)));
    final counts = days
        .map((day) => levels
            .map((level) => events.where((e) {
                  final stamp =
                      DateTime.tryParse(e['at'].toString())?.toLocal();
                  return DateUtils.isSameDay(stamp, day) &&
                      e['status'] == level;
                }).length)
            .toList())
        .toList();
    final maxCount = counts
        .map((row) => row.reduce((a, b) => a + b))
        .fold(1, (a, b) => a > b ? a : b);
    return Card(
        child: Padding(
            padding: const EdgeInsets.all(12),
            child:
                Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              const Text('Past seven days'),
              const SizedBox(height: 12),
              Row(
                  crossAxisAlignment: CrossAxisAlignment.end,
                  children: List.generate(
                      7,
                      (i) => Expanded(
                          child: Semantics(
                              label:
                                  '${days[i].day}: ${List.generate(3, (j) => "${levels[j]} ${counts[i][j]}").join(", ")}',
                              child: Column(children: [
                                Text('${counts[i].reduce((a, b) => a + b)}'),
                                for (var j = 0; j < 3; j++)
                                  Container(
                                      width: 18,
                                      height: 48 * counts[i][j] / maxCount,
                                      color: colors[j]),
                                const Divider(),
                                Text('${days[i].day}')
                              ]))))),
              Wrap(
                  spacing: 12,
                  children: List.generate(
                      3,
                      (j) => Row(mainAxisSize: MainAxisSize.min, children: [
                            Icon(Icons.circle, size: 10, color: colors[j]),
                            const SizedBox(width: 4),
                            Text(levels[j])
                          ]))),
            ])));
  }
}
