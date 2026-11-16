import 'package:flutter/material.dart';
import 'dart:convert';
import '../../../../shared/widgets/medicine_form.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../../core/theme/app_theme.dart';
import '../../../../core/di/providers.dart';

class OnboardingPage extends ConsumerStatefulWidget {
  const OnboardingPage({super.key});

  @override
  ConsumerState<OnboardingPage> createState() => _OnboardingPageState();
}

class _OnboardingPageState extends ConsumerState<OnboardingPage> {
  final _medicines = <Map<String, dynamic>>[];
  String _dietInstructions = '';
  final PageController _pageController = PageController();
  int _currentStep = 0;

  // Form data
  String _gender = '';
  DateTime? _dob;
  int? _heightCm;
  double? _weightKg;
  String _livingSituation = '';
  String _primaryCondition = '';
  String? _surgeryType;
  DateTime? _dischargeDate;
  final List<String> _chronicDiseases = [];
  final List<String> _allergies = [];
  String _eatingHabits = '';
  String _exerciseFrequency = '';
  bool _smoking = false;
  bool _alcohol = false;
  double _sleepBaseline = 5;
  double _moodBaseline = 5;
  Map<String, String>? _emergencyContact;
  bool _isLoading = false;

  final List<String> _genderOptions = [
    'Male',
    'Female',
    'Other',
    'Prefer not to say'
  ];
  final List<String> _livingOptions = [
    'Alone',
    'With family',
    'With caregiver',
    'Assisted living'
  ];
  final List<String> _eatingOptions = [
    'Balanced',
    'Vegetarian',
    'Vegan',
    'Jain',
    'Non-vegetarian',
    'Other'
  ];
  final List<String> _exerciseOptions = [
    'None',
    'Light (walking)',
    'Moderate',
    'Active',
    'Very active'
  ];
  final List<String> _chronicOptions = [
    'Diabetes',
    'Hypertension',
    'Heart disease',
    'Asthma',
    'COPD',
    'Kidney disease',
    'None'
  ];
  final List<String> _conditionOptions = [
    'Appendectomy',
    'Cholecystectomy',
    'Knee replacement',
    'Hip replacement',
    'Cardiac surgery',
    'Spinal surgery',
    'Other'
  ];

  @override
  void dispose() {
    _pageController.dispose();
    super.dispose();
  }

  bool _restoring = true;
  @override
  void initState() {
    super.initState();
    _restoreDraft();
  }

  Future<String> _draftKey() async {
    final api = ref.read(apiClientProvider);
    return api.storageKey('discharge:${await api.account()}');
  }

  Future<void> _restoreDraft() async {
    final store = ref.read(secureStorageProvider);
    try {
      final value = await store.read(key: await _draftKey());
      if (value == null || !mounted) return;
      final d = jsonDecode(value);
      _dob = DateTime.tryParse(d['dob'] ?? '');
      _dischargeDate = DateTime.tryParse(d['discharge'] ?? '');
      _gender = d['gender'];
      _heightCm = d['height'];
      _weightKg = d['weight'];
      _livingSituation = d['living'];
      _primaryCondition = d['condition'];
      _surgeryType = d['procedure'];
      _chronicDiseases.addAll(List<String>.from(d['chronic']));
      _allergies.addAll(List<String>.from(d['allergies']));
      _eatingHabits = d['eating'];
      _exerciseFrequency = d['exercise'];
      _smoking = d['smoking'];
      _alcohol = d['alcohol'];
      _sleepBaseline = d['sleep'];
      _moodBaseline = d['mood'];
      _currentStep = d['step'];
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (mounted && _pageController.hasClients)
          _pageController.jumpToPage(d['step']);
      });
    } finally {
      if (mounted) setState(() => _restoring = false);
    }
  }

  Future<void> _nextStep() async {
    if ((_currentStep == 0 && _dob == null) ||
        (_currentStep == 1 &&
            (_dischargeDate == null || _primaryCondition.isEmpty))) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
          content: Text(_currentStep == 0
              ? 'Enter your birth date to continue.'
              : 'Enter your discharge date and condition.')));
      return;
    }
    if (_currentStep < 3) {
      final store = ref.read(secureStorageProvider);
      await store.write(
          key: await _draftKey(),
          value: jsonEncode({
            'step': _currentStep + 1,
            'dob': _dob?.toIso8601String(),
            'discharge': _dischargeDate?.toIso8601String(),
            'gender': _gender,
            'height': _heightCm,
            'weight': _weightKg,
            'living': _livingSituation,
            'condition': _primaryCondition,
            'procedure': _surgeryType,
            'chronic': _chronicDiseases,
            'allergies': _allergies,
            'eating': _eatingHabits,
            'exercise': _exerciseFrequency,
            'smoking': _smoking,
            'alcohol': _alcohol,
            'sleep': _sleepBaseline,
            'mood': _moodBaseline
          }));
      if (!mounted) return;
      _pageController.nextPage(
        duration: const Duration(milliseconds: 300),
        curve: Curves.easeInOut,
      );
    } else {
      _completeOnboarding();
    }
  }

  void _prevStep() {
    if (_currentStep > 0) {
      _pageController.previousPage(
        duration: const Duration(milliseconds: 300),
        curve: Curves.easeInOut,
      );
    }
  }

  Future<void> _completeOnboarding() async {
    setState(() => _isLoading = true);

    try {
      final apiClient = ref.read(apiClientProvider);

      // Step 1: Demographics
      await apiClient.post('/api/v1/patients/onboarding/step/1', body: {
        'dob': _dob?.toIso8601String().split('T')[0],
        'gender': _gender,
        'height_cm': _heightCm,
        'weight_kg': _weightKg,
        'living_situation': _livingSituation,
      });

      // Step 2: Condition
      await apiClient.post('/api/v1/patients/onboarding/step/2', body: {
        'primary_condition': _primaryCondition,
        'surgery_type': _surgeryType,
        'discharge_date': _dischargeDate?.toIso8601String().split('T')[0],
        'chronic_diseases': _chronicDiseases,
        'allergies': _allergies,
      });

      // Step 3: Lifestyle
      await apiClient.post('/api/v1/patients/onboarding/step/3', body: {
        'eating_habits': _eatingHabits,
        'exercise_frequency': _exerciseFrequency,
        'smoking': _smoking,
        'alcohol': _alcohol,
        'sleep_baseline': _sleepBaseline,
        'mood_baseline': _moodBaseline,
      });

      // Step 4: Emergency contact
      await apiClient.post('/api/v1/patients/onboarding/step/4', body: {
        'emergency_contact': _emergencyContact,
        'discharge_instructions': _dietInstructions,
        'prescriptions': _medicines,
      });

      await ref.read(secureStorageProvider).delete(key: await _draftKey());
      if (!mounted) return;
      ref.invalidate(authStateProvider);

      if (mounted) {
        context.go('/home');
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error: ${e.toString()}')),
        );
      }
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_restoring)
      return const Scaffold(body: Center(child: CircularProgressIndicator()));
    return Scaffold(
      body: SafeArea(
        child: Column(
          children: [
            // Progress indicator
            Padding(
              padding: const EdgeInsets.all(24),
              child: Row(
                children: List.generate(
                    4,
                    (i) => Expanded(
                          child: Container(
                            height: 4,
                            margin: const EdgeInsets.symmetric(horizontal: 2),
                            decoration: BoxDecoration(
                              color: i <= _currentStep
                                  ? AppColors.sage
                                  : AppColors.sagePale,
                              borderRadius: BorderRadius.circular(2),
                            ),
                          ),
                        )),
              ),
            ),

            // Page content
            Expanded(
              child: PageView(
                controller: _pageController,
                physics: const NeverScrollableScrollPhysics(),
                onPageChanged: (i) => setState(() => _currentStep = i),
                children: [
                  _buildStep1(),
                  _buildStep2(),
                  _buildStep3(),
                  _buildStep4(),
                ],
              ),
            ),

            // Navigation buttons
            Padding(
              padding: const EdgeInsets.all(24),
              child: Row(
                children: [
                  if (_currentStep > 0)
                    TextButton(
                      onPressed: _prevStep,
                      child: const Text('Back'),
                    ),
                  const Spacer(),
                  ElevatedButton(
                    onPressed: _isLoading ? null : _nextStep,
                    child: _isLoading
                        ? const SizedBox(
                            height: 20,
                            width: 20,
                            child: CircularProgressIndicator(strokeWidth: 2),
                          )
                        : Text(_currentStep == 3 ? 'Complete' : 'Continue'),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildStep1() {
    return SingleChildScrollView(
      padding: const EdgeInsets.symmetric(horizontal: 24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('About you', style: AppTextStyles.heading()),
          const SizedBox(height: 8),
          Text(
            'Let\'s get to know you better. This helps us personalize your recovery plan.',
            style: AppTextStyles.body(color: AppColors.textMid),
          ),
          const SizedBox(height: 32),

          // Gender
          Text('Gender', style: AppTextStyles.label()),
          const SizedBox(height: 8),
          Wrap(
            spacing: 8,
            children: _genderOptions
                .map((g) => ChoiceChip(
                      label: Text(g),
                      selected: _gender == g,
                      onSelected: (_) => setState(() => _gender = g),
                      selectedColor: AppColors.sagePale,
                    ))
                .toList(),
          ),
          const SizedBox(height: 24),

          // DOB
          Text('Date of birth', style: AppTextStyles.label()),
          const SizedBox(height: 8),
          InkWell(
            onTap: () async {
              final date = await showDatePicker(
                context: context,
                initialDate: _dob ?? DateTime(1980),
                firstDate: DateTime(1920),
                lastDate: DateTime.now(),
              );
              if (date != null) setState(() => _dob = date);
            },
            child: Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: AppColors.cream,
                borderRadius: BorderRadius.circular(14),
              ),
              child: Row(
                children: [
                  const Icon(Icons.calendar_today, color: AppColors.textMid),
                  const SizedBox(width: 12),
                  Text(
                    _dob != null
                        ? '${_dob!.day}/${_dob!.month}/${_dob!.year}'
                        : 'Select date',
                    style: AppTextStyles.body(
                        color: _dob == null ? AppColors.textLight : null),
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 24),

          // Height & Weight
          Row(
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('Height (cm)', style: AppTextStyles.label()),
                    const SizedBox(height: 8),
                    TextFormField(
                      keyboardType: TextInputType.number,
                      initialValue: _heightCm?.toString(),
                      decoration: const InputDecoration(hintText: '170'),
                      onChanged: (v) => _heightCm = int.tryParse(v),
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 16),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('Weight (kg)', style: AppTextStyles.label()),
                    const SizedBox(height: 8),
                    TextFormField(
                      keyboardType: TextInputType.number,
                      initialValue: _weightKg?.toString(),
                      decoration: const InputDecoration(hintText: '70'),
                      onChanged: (v) => _weightKg = double.tryParse(v),
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 24),

          // Living situation
          Text('Living situation', style: AppTextStyles.label()),
          const SizedBox(height: 8),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: _livingOptions
                .map((l) => ChoiceChip(
                      label: Text(l),
                      selected: _livingSituation == l,
                      onSelected: (_) => setState(() => _livingSituation = l),
                      selectedColor: AppColors.sagePale,
                    ))
                .toList(),
          ),
        ],
      ),
    );
  }

  Widget _buildStep2() {
    return SingleChildScrollView(
      padding: const EdgeInsets.symmetric(horizontal: 24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('Your health', style: AppTextStyles.heading()),
          const SizedBox(height: 8),
          Text(
            'Tell us about your recent hospital stay so we can support your recovery.',
            style: AppTextStyles.body(color: AppColors.textMid),
          ),
          const SizedBox(height: 32),

          // Primary condition
          Text('What type of surgery or procedure did you have?',
              style: AppTextStyles.label()),
          const SizedBox(height: 8),
          DropdownButtonFormField<String>(
            initialValue: _primaryCondition.isEmpty ? null : _primaryCondition,
            decoration: const InputDecoration(hintText: 'Select procedure'),
            items: _conditionOptions
                .map((c) => DropdownMenuItem(
                      value: c,
                      child: Text(c),
                    ))
                .toList(),
            onChanged: (v) => setState(() => _primaryCondition = v ?? ''),
          ),
          const SizedBox(height: 24),

          // Surgery type (optional)
          Text('Specific surgery (optional)', style: AppTextStyles.label()),
          const SizedBox(height: 8),
          TextFormField(
            decoration: const InputDecoration(
                hintText: 'e.g., Laparoscopic appendectomy'),
            onChanged: (v) => _surgeryType = v,
          ),
          const SizedBox(height: 24),

          // Discharge date
          Text('When were you discharged?', style: AppTextStyles.label()),
          const SizedBox(height: 8),
          InkWell(
            onTap: () async {
              final date = await showDatePicker(
                context: context,
                initialDate: _dischargeDate ?? DateTime.now(),
                firstDate: DateTime.now().subtract(const Duration(days: 30)),
                lastDate: DateTime.now(),
              );
              if (date != null) setState(() => _dischargeDate = date);
            },
            child: Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: AppColors.cream,
                borderRadius: BorderRadius.circular(14),
              ),
              child: Row(
                children: [
                  const Icon(Icons.calendar_today, color: AppColors.textMid),
                  const SizedBox(width: 12),
                  Text(
                    _dischargeDate != null
                        ? '${_dischargeDate!.day}/${_dischargeDate!.month}/${_dischargeDate!.year}'
                        : 'Select date',
                    style: AppTextStyles.body(
                        color: _dischargeDate == null
                            ? AppColors.textLight
                            : null),
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 24),

          // Chronic diseases
          Text('Any existing health conditions?', style: AppTextStyles.label()),
          const SizedBox(height: 8),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: _chronicOptions
                .map((c) => FilterChip(
                      label: Text(c),
                      selected: _chronicDiseases.contains(c),
                      onSelected: (selected) {
                        setState(() {
                          if (selected) {
                            _chronicDiseases.add(c);
                          } else {
                            _chronicDiseases.remove(c);
                          }
                        });
                      },
                      selectedColor: AppColors.sagePale,
                    ))
                .toList(),
          ),
          const SizedBox(height: 24),

          // Allergies
          Text('Any allergies?', style: AppTextStyles.label()),
          const SizedBox(height: 8),
          Wrap(
            spacing: 8,
            children: ['Penicillin', 'Painkillers', 'Food', 'None']
                .map((a) => FilterChip(
                      label: Text(a),
                      selected: _allergies.contains(a),
                      onSelected: (selected) {
                        setState(() {
                          if (selected) {
                            _allergies.add(a);
                          } else {
                            _allergies.remove(a);
                          }
                        });
                      },
                      selectedColor: AppColors.sagePale,
                    ))
                .toList(),
          ),
        ],
      ),
    );
  }

  Widget _buildStep3() {
    return SingleChildScrollView(
      padding: const EdgeInsets.symmetric(horizontal: 24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('Lifestyle', style: AppTextStyles.heading()),
          const SizedBox(height: 8),
          Text(
            'A few questions about your daily habits to help us understand your baseline.',
            style: AppTextStyles.body(color: AppColors.textMid),
          ),
          const SizedBox(height: 32),

          // Eating habits
          Text('Diet type', style: AppTextStyles.label()),
          const SizedBox(height: 8),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: _eatingOptions
                .map((e) => ChoiceChip(
                      label: Text(e),
                      selected: _eatingHabits == e,
                      onSelected: (_) => setState(() => _eatingHabits = e),
                      selectedColor: AppColors.sagePale,
                    ))
                .toList(),
          ),
          const SizedBox(height: 24),

          // Exercise
          Text('Exercise frequency', style: AppTextStyles.label()),
          const SizedBox(height: 8),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: _exerciseOptions
                .map((e) => ChoiceChip(
                      label: Text(e),
                      selected: _exerciseFrequency == e,
                      onSelected: (_) => setState(() => _exerciseFrequency = e),
                      selectedColor: AppColors.sagePale,
                    ))
                .toList(),
          ),
          const SizedBox(height: 24),

          // Smoking & Alcohol
          Row(
            children: [
              Expanded(
                child: SwitchListTile(
                  title: const Text('Smoking'),
                  value: _smoking,
                  onChanged: (v) => setState(() => _smoking = v),
                  activeThumbColor: AppColors.sage,
                  contentPadding: EdgeInsets.zero,
                ),
              ),
              Expanded(
                child: SwitchListTile(
                  title: const Text('Alcohol'),
                  value: _alcohol,
                  onChanged: (v) => setState(() => _alcohol = v),
                  activeThumbColor: AppColors.sage,
                  contentPadding: EdgeInsets.zero,
                ),
              ),
            ],
          ),
          const SizedBox(height: 24),

          // Sleep baseline
          Text('How would you rate your usual sleep quality?',
              style: AppTextStyles.label()),
          const SizedBox(height: 16),
          Row(
            children: [
              const Text('Poor', style: TextStyle(color: AppColors.textLight)),
              Expanded(
                child: Slider(
                  value: _sleepBaseline,
                  min: 1,
                  max: 10,
                  divisions: 9,
                  label: _sleepBaseline.round().toString(),
                  onChanged: (v) => setState(() => _sleepBaseline = v),
                ),
              ),
              const Text('Great', style: TextStyle(color: AppColors.textLight)),
            ],
          ),
          const SizedBox(height: 16),

          // Mood baseline
          Text('How would you rate your usual mood?',
              style: AppTextStyles.label()),
          const SizedBox(height: 16),
          Row(
            children: [
              const Text('Low', style: TextStyle(color: AppColors.textLight)),
              Expanded(
                child: Slider(
                  value: _moodBaseline,
                  min: 1,
                  max: 10,
                  divisions: 9,
                  label: _moodBaseline.round().toString(),
                  onChanged: (v) => setState(() => _moodBaseline = v),
                ),
              ),
              const Text('Great', style: TextStyle(color: AppColors.textLight)),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildStep4() {
    return SingleChildScrollView(
      padding: const EdgeInsets.symmetric(horizontal: 24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('Almost done', style: AppTextStyles.heading()),
          const SizedBox(height: 8),
          Text(
            'Add an emergency contact so we know who to reach if needed.',
            style: AppTextStyles.body(color: AppColors.textMid),
          ),
          const SizedBox(height: 32),

          TextFormField(
              maxLines: 3,
              maxLength: 4000,
              decoration: const InputDecoration(
                  labelText: 'Food and care instructions from your doctor'),
              onChanged: (value) => _dietInstructions = value),
          for (final med in _medicines)
            ListTile(
                title: Text(med['drug_name']),
                subtitle: Text(med['dosage']),
                trailing: IconButton(
                    icon: const Icon(Icons.close),
                    onPressed: () => setState(() => _medicines.remove(med)))),
          OutlinedButton(
              onPressed: () async {
                final med = await medicineForm(context);
                if (med != null && mounted) setState(() => _medicines.add(med));
              },
              child: const Text('Add discharge prescription')),
          // Emergency contact (optional)
          Text('Emergency contact name', style: AppTextStyles.label()),
          const SizedBox(height: 8),
          TextFormField(
            decoration: const InputDecoration(hintText: 'Contact name'),
            onChanged: (v) =>
                _emergencyContact = {...?_emergencyContact, 'name': v},
          ),
          const SizedBox(height: 16),

          Text('Emergency contact phone', style: AppTextStyles.label()),
          const SizedBox(height: 8),
          TextFormField(
            keyboardType: TextInputType.phone,
            decoration: const InputDecoration(hintText: '+91 98765 43210'),
            onChanged: (v) =>
                _emergencyContact = {...?_emergencyContact, 'phone': v},
          ),
          const SizedBox(height: 32),

          // Summary card
          Container(
            padding: const EdgeInsets.all(20),
            decoration: BoxDecoration(
              color: AppColors.sagePale,
              borderRadius: BorderRadius.circular(20),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    const Icon(Icons.check_circle,
                        color: AppColors.sage, size: 24),
                    const SizedBox(width: 12),
                    Text('Your recovery plan is ready',
                        style: AppTextStyles.body(weight: FontWeight.w500)),
                  ],
                ),
                const SizedBox(height: 16),
                Text(
                  'We\'ll send you gentle daily check-ins and track your recovery trends. '
                  'Your data stays private and secure.',
                  style: AppTextStyles.caption(),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
