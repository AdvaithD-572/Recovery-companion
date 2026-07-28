import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:speech_to_text/speech_to_text.dart';
import 'package:flutter_tts/flutter_tts.dart';
import 'package:go_router/go_router.dart';

import '../../../../core/theme/app_theme.dart';
import '../../../../core/di/providers.dart';

/// Voice bot state machine states
enum _BotState { selectingLanguage, loading, speaking, listening, processing, done, error }

class VoiceSessionPage extends ConsumerStatefulWidget {
  const VoiceSessionPage({super.key});

  @override
  ConsumerState<VoiceSessionPage> createState() => _VoiceSessionPageState();
}

class _VoiceSessionPageState extends ConsumerState<VoiceSessionPage> {
  final SpeechToText _speech = SpeechToText();
  final FlutterTts _tts = FlutterTts();

  _BotState _state = _BotState.selectingLanguage;
  String _currentLanguage = 'en-US';
  String _statusText = '';
  String _recognizedText = '';
  int _currentQuestion = 0;
  final List<int> _answers = [];

  List<_VoiceQuestion> _questions = [
    _VoiceQuestion('How are you feeling today? Rate your pain from 0 to 10.', 'pain_score'),
    _VoiceQuestion('How was your sleep last night? Give a number from 0 to 10.', 'sleep_score'),
    _VoiceQuestion("How's your appetite? Rate from 0 to 10.", 'appetite_score'),
    _VoiceQuestion("How's your mood? Give a number from 0 to 10.", 'mood_score'),
    _VoiceQuestion("How's your energy today? Rate from 0 to 10.", 'fatigue_score'),
    _VoiceQuestion("How's your mobility? Rate from 0 to 10.", 'mobility_score'),
  ];

  static const _languages = [
    {'code': 'en-US', 'label': 'English', 'flag': '🇬🇧'},
    {'code': 'hi-IN', 'label': 'हिंदी', 'flag': '🇮🇳'},
    {'code': 'te-IN', 'label': 'తెలుగు', 'flag': '🇮🇳'},
    {'code': 'ta-IN', 'label': 'தமிழ்', 'flag': '🇮🇳'},
  ];

  static const _openings = {
    'en-US': 'Hello! Starting your daily check-in. I will ask you 6 questions. Answer each with a number from 0 to 10.',
    'hi-IN': 'नमस्ते! आपका दैनिक चेक-इन शुरू हो रहा है। मैं आपसे 6 सवाल पूछूंगा। हर जवाब 0 से 10 के बीच में दें।',
    'te-IN': 'నమస్కారం! మీ రోజువారీ చెక్-ఇన్ ప్రారంభమవుతోంది. నేను మీకు 6 ప్రశ్నలు అడుగుతాను. ప్రతి సమాధానం 0 నుండి 10 మధ్య ఇవ్వండి.',
    'ta-IN': 'வணக்கம்! உங்கள் தினசரி செக்-இன் தொடங்குகிறது. நான் 6 கேள்விகள் கேட்பேன். பூஜ்யம் முதல் 10 வரை கொடுங்கள்.',
  };

  static const _retryMessages = {
    'en-US': 'Please say a number from 0 to 10.',
    'hi-IN': 'कृपया 0 से 10 के बीच एक नंबर कहें।',
    'te-IN': 'దయచేసి 0 నుండి 10 మధ్య ఒక సంఖ్య చెప్పండి.',
    'ta-IN': '0 முதல் 10 வரை ஒரு எண் சொல்லுங்கள்.',
  };

  static const _doneMessages = {
    'en-US': 'Thank you! Your check-in has been saved. Take care!',
    'hi-IN': 'धन्यवाद! आपका चेक-इन सेव हो गया है। अपना ख्याल रखें!',
    'te-IN': 'ధన్యవాదాలు! మీ చెక్-ఇన్ సేవ్ చేయబడింది. జాగ్రత్తగా ఉండండి!',
    'ta-IN': 'நன்றி! உங்கள் செக்-இன் சேமிக்கப்பட்டது. கவனமாக இருங்கள்!',
  };

  @override
  void initState() {
    super.initState();
    _tts.awaitSpeakCompletion(true);
  }

  // ──────────────────────────────────────────────
  // Language selection → starts the session
  // ──────────────────────────────────────────────
  Future<void> _startSession(String languageCode) async {
    setState(() {
      _currentLanguage = languageCode;
      _state = _BotState.loading;
      _statusText = 'Loading questions…';
    });

    await _tts.setLanguage(languageCode);
    await _tts.setSpeechRate(0.45);

    // Fetch translated questions if not English
    if (!languageCode.startsWith('en')) {
      try {
        final apiClient = ref.read(apiClientProvider);
        final response = await apiClient.get(
          '/api/v1/voice/localize',
          queryParams: {'language': languageCode},
        );
        if (response != null && response['questions'] != null) {
          final rq = response['questions'] as List<dynamic>;
          setState(() {
            _questions = rq
                .map((q) => _VoiceQuestion(q['text'] as String, q['field'] as String))
                .toList();
          });
        }
      } catch (_) {
        // Keep English questions
      }
    }

    // Init microphone
    final available = await _speech.initialize(
      onStatus: (s) {
        if (mounted && s == 'done' && _state == _BotState.listening) {
          // STT timed out without result → retry
          _handleNoSpeech();
        }
      },
      onError: (e) {
        if (mounted && _state == _BotState.listening) _handleNoSpeech();
      },
    );

    if (!available) {
      if (mounted) setState(() { _state = _BotState.error; _statusText = 'Microphone not available'; });
      return;
    }

    // Speak opening then begin Q&A
    await _speakAndWait(_openings[languageCode] ?? _openings['en-US']!);
    _askCurrentQuestion();
  }

  // ──────────────────────────────────────────────
  // Ask question → then listen
  // ──────────────────────────────────────────────
  Future<void> _askCurrentQuestion() async {
    if (!mounted) return;
    setState(() {
      _state = _BotState.speaking;
      _statusText = _questions[_currentQuestion].text;
      _recognizedText = '';
    });

    await _speakAndWait(_questions[_currentQuestion].text);
    _startListening();
  }

  // ──────────────────────────────────────────────
  // Reliable TTS wait using Completer
  // ──────────────────────────────────────────────
  Future<void> _speakAndWait(String text) async {
    // awaitSpeakCompletion(true) makes speak() itself block until done
    await _tts.speak(text);
    await Future.delayed(const Duration(milliseconds: 250));
  }

  // ──────────────────────────────────────────────
  // Listen for user answer
  // ──────────────────────────────────────────────
  void _startListening() {
    if (!mounted) return;
    setState(() {
      _state = _BotState.listening;
      _statusText = 'Listening…';
      _recognizedText = '';
    });

    _speech.listen(
      localeId: _currentLanguage,
      listenOptions: SpeechListenOptions(
        listenMode: ListenMode.confirmation,
        cancelOnError: false,
      ),
      onResult: (result) {
        if (!mounted) return;
        setState(() => _recognizedText = result.recognizedWords);

        if (result.finalResult) {
          _speech.stop();
          if (_recognizedText.trim().isEmpty) {
            _handleNoSpeech();
          } else {
            _processAnswer(_recognizedText);
          }
        }
      },
    );
  }

  void _handleNoSpeech() {
    if (_state != _BotState.listening) return;
    // Retry asking the same question
    _askCurrentQuestion();
  }

  // ──────────────────────────────────────────────
  // Process answer → extract number → advance
  // ──────────────────────────────────────────────
  Future<void> _processAnswer(String text) async {
    if (!mounted) return;
    setState(() { _state = _BotState.processing; });

    final score = _extractScore(text);
    if (score == null) {
      // Couldn't extract — ask to repeat
      await _speakAndWait(_retryMessages[_currentLanguage] ?? _retryMessages['en-US']!);
      _askCurrentQuestion();
      return;
    }

    _answers.add(score);

    if (_currentQuestion < _questions.length - 1) {
      setState(() => _currentQuestion++);
      _askCurrentQuestion();
    } else {
      await _submitAndClose();
    }
  }

  int? _extractScore(String text) {
    final t = text.toLowerCase().trim();

    // Digit anywhere in text
    final numMatch = RegExp(r'\b(\d{1,2})\b').firstMatch(t);
    if (numMatch != null) {
      final n = int.tryParse(numMatch.group(1)!);
      if (n != null && n >= 0 && n <= 10) return n;
    }

    // Word maps (English + Hindi + Telugu)
    const words = {
      'zero': 0, 'one': 1, 'two': 2, 'three': 3, 'four': 4,
      'five': 5, 'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10,
      'शून्य': 0, 'एक': 1, 'दो': 2, 'तीन': 3, 'चार': 4,
      'पांच': 5, 'पाँच': 5, 'छह': 6, 'सात': 7, 'आठ': 8, 'नौ': 9, 'दस': 10,
      'సున్న': 0, 'ఒకటి': 1, 'రెండు': 2, 'మూడు': 3, 'నాలుగు': 4,
      'అయిదు': 5, 'ఆరు': 6, 'ఏడు': 7, 'ఎనిమిది': 8, 'తొమ్మిది': 9, 'పది': 10,
    };
    for (final e in words.entries) {
      if (t.contains(e.key)) return e.value;
    }

    // Common English descriptor fallback
    const desc = {
      'great': 8, 'good': 7, 'fine': 6, 'okay': 5, 'ok': 5,
      'bad': 3, 'terrible': 1, 'worst': 0, 'excellent': 9, 'perfect': 10,
    };
    for (final e in desc.entries) {
      if (t.contains(e.key)) return e.value;
    }

    return null;
  }

  // ──────────────────────────────────────────────
  // Submit results to backend
  // ──────────────────────────────────────────────
  Future<void> _submitAndClose() async {
    setState(() { _state = _BotState.done; });
    await _speakAndWait(_doneMessages[_currentLanguage] ?? _doneMessages['en-US']!);

    try {
      final apiClient = ref.read(apiClientProvider);
      final today = DateTime.now().toIso8601String().split('T')[0];
      await apiClient.post('/api/v1/logs/daily', body: {
        'log_date': today,
        'pain_score':     _answers.isNotEmpty     ? _answers[0] : 5,
        'sleep_score':    _answers.length > 1     ? _answers[1] : 5,
        'appetite_score': _answers.length > 2     ? _answers[2] : 5,
        'mood_score':     _answers.length > 3     ? _answers[3] : 5,
        'fatigue_score':  _answers.length > 4     ? _answers[4] : 5,
        'mobility_score': _answers.length > 5     ? _answers[5] : 5,
        'submission_method': 'voice',
      });
      ref.invalidate(todayLogProvider);
    } catch (_) {}

    if (mounted) {
      await Future.delayed(const Duration(seconds: 1));
      if (mounted) context.pop();
    }
  }

  @override
  void dispose() {
    _speech.stop();
    _tts.stop();
    super.dispose();
  }

  // ──────────────────────────────────────────────
  // UI
  // ──────────────────────────────────────────────
  @override
  Widget build(BuildContext context) {
    if (_state == _BotState.selectingLanguage) {
      return _buildLanguagePicker();
    }
    return _buildSession();
  }

  Widget _buildLanguagePicker() {
    return Scaffold(
      backgroundColor: AppColors.warmWhite,
      appBar: AppBar(
        title: const Text('Voice Check-in'),
        backgroundColor: Colors.transparent,
        elevation: 0,
      ),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(32),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.center,
            children: [
              const Spacer(),
              Container(
                width: 80, height: 80,
                decoration: BoxDecoration(color: AppColors.sagePale, shape: BoxShape.circle),
                child: const Icon(Icons.language, color: AppColors.sage, size: 40),
              ),
              const SizedBox(height: 24),
              Text('What language do you speak?', style: AppTextStyles.heading(), textAlign: TextAlign.center),
              const SizedBox(height: 8),
              Text(
                'The bot will ask all questions and understand your answers in your language.',
                style: AppTextStyles.body(color: AppColors.textMid),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 40),
              ..._languages.map((lang) => Padding(
                padding: const EdgeInsets.only(bottom: 12),
                child: SizedBox(
                  width: double.infinity,
                  child: ElevatedButton(
                    style: ElevatedButton.styleFrom(
                      backgroundColor: Colors.white,
                      foregroundColor: AppColors.textDark,
                      elevation: 0,
                      side: const BorderSide(color: AppColors.cream, width: 2),
                      padding: const EdgeInsets.symmetric(vertical: 18),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
                    ),
                    onPressed: () => _startSession(lang['code']!),
                    child: Text(
                      '${lang['flag']} ${lang['label']}',
                      style: AppTextStyles.body(weight: FontWeight.w600),
                    ),
                  ),
                ),
              )),
              const Spacer(),
              TextButton(
                onPressed: () => context.push('/checkin'),
                child: const Text('Use manual input instead'),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildSession() {
    return Scaffold(
      backgroundColor: AppColors.warmWhite,
      appBar: AppBar(
        title: const Text('Voice Check-in'),
        backgroundColor: Colors.transparent,
        elevation: 0,
      ),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            children: [
              const Spacer(),

              // Animated mic circle
              _buildMicAnimation(),

              const SizedBox(height: 32),

              // State label
              Text(
                _state == _BotState.speaking  ? 'Speaking…'   :
                _state == _BotState.listening  ? 'Listening…'  :
                _state == _BotState.loading    ? 'Loading…'    :
                _state == _BotState.processing ? 'Processing…' :
                _state == _BotState.done       ? 'Done!'       : '',
                style: AppTextStyles.heading(size: 22),
              ),
              const SizedBox(height: 12),

              // Showing current question text or recognized words
              AnimatedSwitcher(
                duration: const Duration(milliseconds: 300),
                child: Text(
                  _state == _BotState.listening && _recognizedText.isNotEmpty
                      ? '"$_recognizedText"'
                      : _statusText,
                  key: ValueKey(_statusText + _recognizedText),
                  style: AppTextStyles.body(color: AppColors.textMid),
                  textAlign: TextAlign.center,
                ),
              ),

              const Spacer(),

              // Progress
              if (_answers.isNotEmpty) ...[
                Text(
                  '${_answers.length} / ${_questions.length}',
                  style: AppTextStyles.caption(color: AppColors.textMid),
                ),
                const SizedBox(height: 6),
                LinearProgressIndicator(
                  value: _answers.length / _questions.length,
                  backgroundColor: AppColors.cream,
                  valueColor: const AlwaysStoppedAnimation<Color>(AppColors.sage),
                  minHeight: 6,
                  borderRadius: BorderRadius.circular(3),
                ),
              ],

              const SizedBox(height: 32),

              TextButton(
                onPressed: () => context.push('/checkin'),
                child: const Text('Switch to manual input'),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildMicAnimation() {
    final isActive = _state == _BotState.listening || _state == _BotState.speaking;
    return TweenAnimationBuilder<double>(
      tween: Tween(begin: 1.0, end: isActive ? 1.15 : 1.0),
      duration: const Duration(milliseconds: 700),
      curve: Curves.easeInOut,
      builder: (context, scale, _) => Container(
        width: 140 * scale, height: 140 * scale,
        decoration: BoxDecoration(
          shape: BoxShape.circle,
          color: isActive ? AppColors.sagePale : AppColors.cream,
          boxShadow: isActive ? [
            BoxShadow(color: AppColors.sage.withValues(alpha: 0.25), blurRadius: 30, spreadRadius: 6),
          ] : [],
        ),
        child: Center(
          child: Container(
            width: 100, height: 100,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: _state == _BotState.listening ? AppColors.sage : AppColors.cream,
            ),
            child: Icon(
              _state == _BotState.listening ? Icons.mic :
              _state == _BotState.speaking  ? Icons.volume_up : Icons.mic_none,
              size: 44,
              color: _state == _BotState.listening ? Colors.white : AppColors.sage,
            ),
          ),
        ),
      ),
    );
  }
}

class _VoiceQuestion {
  final String text;
  final String field;
  _VoiceQuestion(this.text, this.field);
}
