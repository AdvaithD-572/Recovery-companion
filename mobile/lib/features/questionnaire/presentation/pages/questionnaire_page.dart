import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../../core/theme/app_theme.dart';
import '../../../../core/di/providers.dart';

class QuestionnairePage extends ConsumerStatefulWidget {
  const QuestionnairePage({super.key});

  @override
  ConsumerState<QuestionnairePage> createState() => _QuestionnairePageState();
}

class _QuestionnairePageState extends ConsumerState<QuestionnairePage> {
  final PageController _pageController = PageController();
  int _currentPage = 0;
  bool _isLoading = false;

  // Scores (0-10)
  int _painScore = 5;
  int _sleepScore = 5;
  int _appetiteScore = 5;
  int _moodScore = 5;
  int _fatigueScore = 5;
  int _mobilityScore = 5;
  int _medicineAdherence = 10;
  final _noteController = TextEditingController();

  final List<_QuestionItem> _questions = [
    _QuestionItem(
      title: 'How would you rate your pain?',
      subtitle: '0 = No pain, 10 = Worst pain imaginable',
      icon: Icons.healing_outlined,
    ),
    _QuestionItem(
      title: 'How was your sleep?',
      subtitle: '0 = Terrible, 10 = Excellent rest',
      icon: Icons.bedtime_outlined,
    ),
    _QuestionItem(
      title: 'How\'s your appetite?',
      subtitle: '0 = No appetite, 10 = Great hunger',
      icon: Icons.restaurant_outlined,
    ),
    _QuestionItem(
      title: 'How\'s your mood?',
      subtitle: '0 = Very low, 10 = Great mood',
      icon: Icons.mood_outlined,
    ),
    _QuestionItem(
      title: 'How\'s your energy level?',
      subtitle: '0 = Exhausted, 10 = Full of energy',
      icon: Icons.bolt_outlined,
    ),
    _QuestionItem(
      title: 'How\'s your mobility?',
      subtitle: '0 = Bedridden, 10 = Fully mobile',
      icon: Icons.directions_walk_outlined,
    ),
  ];

  Future<void> _submit() async {
    setState(() => _isLoading = true);
    
    try {
      final apiClient = ref.read(apiClientProvider);
      final today = DateTime.now().toIso8601String().split('T')[0];
      
      await apiClient.post('/api/v1/logs/daily', body: {
        'log_date': today,
        'pain_score': _painScore,
        'sleep_score': _sleepScore,
        'appetite_score': _appetiteScore,
        'mood_score': _moodScore,
        'fatigue_score': _fatigueScore,
        'mobility_score': _mobilityScore,
        'medicine_adherence': _medicineAdherence,
        'note': _noteController.text.isEmpty ? null : _noteController.text,
        'submission_method': 'manual',
      });

      // Invalidate the today log cache
      ref.invalidate(todayLogProvider);

      if (mounted) {
        _showSuccessAndPop();
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

  void _showSuccessAndPop() {
    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (context) => AlertDialog(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(24)),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: 80, height: 80,
              decoration: BoxDecoration(
                color: AppColors.sagePale,
                shape: BoxShape.circle,
              ),
              child: const Icon(Icons.check_circle, color: AppColors.sage, size: 48),
            ),
            const SizedBox(height: 24),
            Text('Check-in complete!', style: AppTextStyles.heading()),
            const SizedBox(height: 8),
            Text(
              'Great job tracking your recovery. See you tomorrow!',
              style: AppTextStyles.body(color: AppColors.textMid),
              textAlign: TextAlign.center,
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () {
              Navigator.of(context).pop();
              context.pop();
            },
            child: const Text('Done'),
          ),
        ],
      ),
    );
  }

  void _nextPage() {
    if (_currentPage < _questions.length) {
      _pageController.nextPage(
        duration: const Duration(milliseconds: 300),
        curve: Curves.easeInOut,
      );
    } else {
      _submit();
    }
  }

  void _prevPage() {
    if (_currentPage > 0) {
      _pageController.previousPage(
        duration: const Duration(milliseconds: 300),
        curve: Curves.easeInOut,
      );
    }
  }

  @override
  void dispose() {
    _pageController.dispose();
    _noteController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Daily check-in'),
        leading: IconButton(
          icon: const Icon(Icons.close),
          onPressed: () => context.pop(),
        ),
      ),
      body: Column(
        children: [
          // Progress
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
            child: Row(
              children: List.generate(_questions.length + 1, (i) => Expanded(
                child: Container(
                  height: 4,
                  margin: const EdgeInsets.symmetric(horizontal: 2),
                  decoration: BoxDecoration(
                    color: i <= _currentPage ? AppColors.sage : AppColors.sagePale,
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
              onPageChanged: (i) => setState(() => _currentPage = i),
              children: [
                ..._questions.asMap().entries.map((entry) => _buildQuestionPage(entry.key)),
                _buildNotePage(),
              ],
            ),
          ),

          // Navigation
          Padding(
            padding: const EdgeInsets.all(24),
            child: Row(
              children: [
                if (_currentPage > 0)
                  TextButton(onPressed: _prevPage, child: const Text('Back')),
                const Spacer(),
                ElevatedButton(
                  onPressed: _isLoading ? null : _nextPage,
                  child: _isLoading
                    ? const SizedBox(height: 20, width: 20, child: CircularProgressIndicator(strokeWidth: 2))
                    : Text(_currentPage < _questions.length ? 'Continue' : 'Save'),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildQuestionPage(int index) {
    final question = _questions[index];
    int value;
    switch (index) {
      case 0: value = _painScore; break;
      case 1: value = _sleepScore; break;
      case 2: value = _appetiteScore; break;
      case 3: value = _moodScore; break;
      case 4: value = _fatigueScore; break;
      case 5: value = _mobilityScore; break;
      default: value = 5;
    }

    return Padding(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Spacer(),
          Container(
            width: 64, height: 64,
            decoration: BoxDecoration(
              color: AppColors.sagePale,
              borderRadius: BorderRadius.circular(20),
            ),
            child: Icon(question.icon, color: AppColors.sage, size: 32),
          ),
          const SizedBox(height: 24),
          Text(question.title, style: AppTextStyles.heading(size: 28)),
          const SizedBox(height: 8),
          Text(question.subtitle, style: AppTextStyles.body(color: AppColors.textMid)),
          const SizedBox(height: 48),
          
          // Large slider
          Center(
            child: Column(
              children: [
                Text('$value', style: AppTextStyles.display(size: 64, color: AppColors.sage)),
                Text(_getEmoji(value), style: const TextStyle(fontSize: 48)),
              ],
            ),
          ),
          const SizedBox(height: 24),
          SliderTheme(
            data: SliderTheme.of(context).copyWith(
              trackHeight: 8,
              thumbShape: const RoundSliderThumbShape(enabledThumbRadius: 16),
            ),
            child: Slider(
              value: value.toDouble(),
              min: 0, max: 10,
              divisions: 10,
              onChanged: (v) => setState(() {
                final newValue = v.round();
                switch (index) {
                  case 0: _painScore = newValue; break;
                  case 1: _sleepScore = newValue; break;
                  case 2: _appetiteScore = newValue; break;
                  case 3: _moodScore = newValue; break;
                  case 4: _fatigueScore = newValue; break;
                  case 5: _mobilityScore = newValue; break;
                }
              }),
            ),
          ),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text('0', style: AppTextStyles.caption()),
              Text('10', style: AppTextStyles.caption()),
            ],
          ),
          const Spacer(),
        ],
      ),
    );
  }

  Widget _buildNotePage() {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const SizedBox(height: 24),
          Text('Anything else?', style: AppTextStyles.heading(size: 28)),
          const SizedBox(height: 8),
          Text(
            'Add a note about how you\'re feeling. This is optional.',
            style: AppTextStyles.body(color: AppColors.textMid),
          ),
          const SizedBox(height: 24),
          TextField(
            controller: _noteController,
            maxLines: 5,
            decoration: InputDecoration(
              hintText: 'How are you feeling today? Any observations...',
              border: OutlineInputBorder(borderRadius: BorderRadius.circular(16)),
            ),
          ),
          const SizedBox(height: 24),
          
          // Medicine adherence
          Text('Did you take your medicines today?', style: AppTextStyles.body(weight: FontWeight.w500)),
          const SizedBox(height: 16),
          Row(
            children: [
              Expanded(
                child: GestureDetector(
                  onTap: () => setState(() => _medicineAdherence = 10),
                  child: Container(
                    padding: const EdgeInsets.all(16),
                    decoration: BoxDecoration(
                      color: _medicineAdherence == 10 ? AppColors.sagePale : AppColors.cream,
                      borderRadius: BorderRadius.circular(16),
                      border: Border.all(
                        color: _medicineAdherence == 10 ? AppColors.sage : Colors.transparent,
                      ),
                    ),
                    child: Column(
                      children: [
                        Icon(Icons.check_circle, color: _medicineAdherence == 10 ? AppColors.sage : AppColors.textLight),
                        const SizedBox(height: 8),
                        Text('Yes, all', style: AppTextStyles.body(weight: FontWeight.w500)),
                      ],
                    ),
                  ),
                ),
              ),
              const SizedBox(width: 16),
              Expanded(
                child: GestureDetector(
                  onTap: () => setState(() => _medicineAdherence = 5),
                  child: Container(
                    padding: const EdgeInsets.all(16),
                    decoration: BoxDecoration(
                      color: _medicineAdherence == 5 ? AppColors.cautionPale : AppColors.cream,
                      borderRadius: BorderRadius.circular(16),
                      border: Border.all(
                        color: _medicineAdherence == 5 ? AppColors.caution : Colors.transparent,
                      ),
                    ),
                    child: Column(
                      children: [
                        Icon(Icons.warning_amber, color: _medicineAdherence == 5 ? AppColors.caution : AppColors.textLight),
                        const SizedBox(height: 8),
                        Text('Some missed', style: AppTextStyles.body(weight: FontWeight.w500)),
                      ],
                    ),
                  ),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  String _getEmoji(int value) {
    if (value <= 2) return '😔';
    if (value <= 4) return '😐';
    if (value <= 6) return '🙂';
    if (value <= 8) return '😊';
    return '😄';
  }
}

class _QuestionItem {
  final String title;
  final String subtitle;
  final IconData icon;

  _QuestionItem({required this.title, required this.subtitle, required this.icon});
}
