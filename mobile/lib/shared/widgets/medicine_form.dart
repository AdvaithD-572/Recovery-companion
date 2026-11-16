import 'package:flutter/material.dart';

Future<Map<String, dynamic>?> medicineForm(BuildContext context,
    {Map<String, dynamic>? draft}) async {
  final form = GlobalKey<FormState>();
  String name = draft?['drug_name']?.toString() ?? '',
      dose = draft?['dosage']?.toString() ?? '',
      times = '',
      stock = '',
      notes = '';
  return showDialog<Map<String, dynamic>>(
      context: context,
      builder: (ctx) => AlertDialog(
              title: const Text('Record a prescription'),
              content: SingleChildScrollView(
                  child: Form(
                      key: form,
                      child: Column(mainAxisSize: MainAxisSize.min, children: [
                        TextFormField(
                            initialValue: name,
                            decoration: const InputDecoration(
                                labelText: 'Medicine name'),
                            onChanged: (v) => name = v,
                            validator: (v) => (v ?? '').trim().length < 2
                                ? 'Enter the prescribed name'
                                : null),
                        TextFormField(
                            initialValue: dose,
                            decoration: const InputDecoration(
                                labelText: 'Dose and unit as prescribed'),
                            onChanged: (v) => dose = v,
                            validator: (v) => (v ?? '').trim().isEmpty
                                ? 'Enter the prescribed dose'
                                : null),
                        TextFormField(
                            decoration: const InputDecoration(
                                labelText: 'Scheduled times (HH:mm, HH:mm)',
                                helperText: 'Leave empty for as-needed use'),
                            onChanged: (v) => times = v,
                            validator: (v) => (v ?? '').trim().isEmpty ||
                                    v!.split(',').every((t) =>
                                        RegExp(r'^([01]\d|2[0-3]):[0-5]\d$')
                                            .hasMatch(t.trim()))
                                ? null
                                : 'Enter 24-hour times'),
                        TextFormField(
                            decoration: const InputDecoration(
                                labelText: 'Doses supplied'),
                            keyboardType: TextInputType.number,
                            onChanged: (v) => stock = v,
                            validator: (v) => (int.tryParse(v ?? '') ?? 0) < 1
                                ? 'Enter the number supplied'
                                : null),
                        TextFormField(
                            decoration: const InputDecoration(
                                labelText: 'Additional instructions'),
                            onChanged: (v) => notes = v)
                      ]))),
              actions: [
                TextButton(
                    onPressed: () => Navigator.pop(ctx),
                    child: const Text('Cancel')),
                FilledButton(
                    onPressed: () {
                      if (form.currentState!.validate()) {
                        Navigator.pop(ctx, {
                          'drug_name': name.trim(),
                          'dosage': dose.trim(),
                          'frequency': {
                            'times': times
                                .split(',')
                                .map((v) => v.trim())
                                .where((v) => v.isNotEmpty)
                                .toSet()
                                .toList()
                          },
                          'is_compulsory': times.trim().isNotEmpty,
                          'total_doses_bought': int.parse(stock.trim()),
                          'start_date':
                              DateTime.now().toIso8601String().split('T').first,
                          'notes': notes
                        });
                      }
                    },
                    child: const Text('Confirm prescription'))
              ]));
}
