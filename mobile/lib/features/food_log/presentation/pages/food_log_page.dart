import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:image_picker/image_picker.dart';

import '../../../../core/theme/app_theme.dart';
import '../../../../core/di/providers.dart';

class FoodLogPage extends ConsumerStatefulWidget {
  const FoodLogPage({super.key});

  @override
  ConsumerState<FoodLogPage> createState() => _FoodLogPageState();
}

class _FoodLogPageState extends ConsumerState<FoodLogPage> {
  final ImagePicker _picker = ImagePicker();
  String _selectedMealType = 'breakfast';
  bool _isLoading = false;
  List<Map<String, dynamic>> _scannedFoods = [];
  bool _showRecommendations = false;

  @override
  Widget build(BuildContext context) {
    final todayLogsAsync = ref.watch(todayFoodLogsProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Food Log'),
        actions: [
          IconButton(
            icon: Icon(_showRecommendations ? Icons.list : Icons.lightbulb_outline),
            onPressed: () => setState(() => _showRecommendations = !_showRecommendations),
          ),
        ],
      ),
      body: _showRecommendations ? _buildRecommendations() : _buildFoodLog(todayLogsAsync),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: _isLoading ? null : _scanFood,
        backgroundColor: AppColors.sage,
        icon: _isLoading
            ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
            : const Icon(Icons.camera_alt),
        label: Text(_isLoading ? 'Scanning...' : 'Scan meal'),
      ),
    );
  }

  Widget _buildFoodLog(AsyncValue<List<Map<String, dynamic>>> todayLogsAsync) {
    return todayLogsAsync.when(
      data: (logs) {
        if (logs.isEmpty) {
          return _buildEmptyState();
        }
        
        return ListView(
          padding: const EdgeInsets.all(24),
          children: [
            // Meal type selector
            SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              child: Row(
                children: ['breakfast', 'lunch', 'dinner', 'snack'].map((type) => Padding(
                  padding: const EdgeInsets.only(right: 8),
                  child: ChoiceChip(
                    label: Text(type[0].toUpperCase() + type.substring(1)),
                    selected: _selectedMealType == type,
                    onSelected: (_) => setState(() => _selectedMealType = type),
                    selectedColor: AppColors.sagePale,
                  ),
                )).toList(),
              ),
            ),
            const SizedBox(height: 24),
            
            // Scanned foods
            if (_scannedFoods.isNotEmpty) ...[
              Text('Scanned foods', style: AppTextStyles.label()),
              const SizedBox(height: 12),
              ..._scannedFoods.map((food) => Container(
                margin: const EdgeInsets.only(bottom: 8),
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: AppColors.bluePale,
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Row(
                  children: [
                    Expanded(child: Text(food['name'] ?? '', style: AppTextStyles.body())),
                    if (food['confidence'] != null)
                      Text('${((food['confidence'] as double) * 100).toInt()}%',
                        style: AppTextStyles.caption(color: AppColors.blue)),
                  ],
                ),
              )),
              const SizedBox(height: 16),
              ElevatedButton(
                onPressed: _submitFoodLog,
                child: const Text('Save meal'),
              ),
              const SizedBox(height: 24),
            ],
            
            // Today's logs
            Text('Today\'s meals', style: AppTextStyles.label()),
            const SizedBox(height: 12),
            ...logs.map((log) => Container(
              margin: const EdgeInsets.only(bottom: 12),
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(16),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Container(
                        padding: const EdgeInsets.all(8),
                        decoration: BoxDecoration(
                          color: AppColors.bluePale,
                          borderRadius: BorderRadius.circular(8),
                        ),
                        child: Icon(_getMealIcon(log['meal_type']), size: 16, color: AppColors.blue),
                      ),
                      const SizedBox(width: 12),
                      Text(log['meal_type']?.toString().toUpperCase() ?? '', style: AppTextStyles.label()),
                      const Spacer(),
                      Text(
                        log['logged_at']?.toString().substring(11, 16) ?? '',
                        style: AppTextStyles.caption(),
                      ),
                    ],
                  ),
                  const SizedBox(height: 12),
                  Text(
                    (log['food_items'] as List?)?.map((i) => i['name']).join(', ') ?? '',
                    style: AppTextStyles.body(),
                  ),
                  if ((log['interaction_flags'] as List?)?.isNotEmpty ?? false) ...[
                    const SizedBox(height: 12),
                    Container(
                      padding: const EdgeInsets.all(8),
                      decoration: BoxDecoration(
                        color: AppColors.cautionPale,
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: Row(
                        children: [
                          const Icon(Icons.info_outline, size: 16, color: AppColors.caution),
                          const SizedBox(width: 8),
                          Expanded(
                            child: Text(
                              (log['interaction_flags'] as List).first['message'] ?? '',
                              style: AppTextStyles.caption(color: AppColors.caution),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ],
              ),
            )),
            const SizedBox(height: 80),
          ],
        );
      },
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (_, __) => const Center(child: Text('Failed to load')),
    );
  }

  Widget _buildEmptyState() {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Container(
              width: 80, height: 80,
              decoration: BoxDecoration(
                color: AppColors.sagePale,
                borderRadius: BorderRadius.circular(24),
              ),
              child: const Icon(Icons.restaurant_outlined, color: AppColors.sage, size: 40),
            ),
            const SizedBox(height: 24),
            Text('Log your meals', style: AppTextStyles.heading()),
            const SizedBox(height: 8),
            Text(
              'Tap the camera button to scan your meal and check for any interactions with your medicines.',
              style: AppTextStyles.body(color: AppColors.textMid),
              textAlign: TextAlign.center,
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildRecommendations() {
    return ListView(
      padding: const EdgeInsets.all(24),
      children: [
        Text('Foods for your recovery', style: AppTextStyles.heading()),
        const SizedBox(height: 8),
        Text(
          'Based on your condition and medicines, these foods may support your recovery.',
          style: AppTextStyles.body(color: AppColors.textMid),
        ),
        const SizedBox(height: 24),
        _buildRecommendedFood('Oatmeal', 'Great for digestion and energy'),
        _buildRecommendedFood('Lean chicken', 'Protein for tissue repair'),
        _buildRecommendedFood('Blueberries', 'Antioxidants for healing'),
        _buildRecommendedFood('Greek yogurt', 'Probiotics for gut health'),
        _buildRecommendedFood('Broccoli', 'Vitamins and fiber'),
        _buildRecommendedFood('Sweet potato', 'Complex carbs for energy'),
        const SizedBox(height: 24),
        Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: AppColors.bluePale,
            borderRadius: BorderRadius.circular(16),
          ),
          child: Row(
            children: [
              const Icon(Icons.info_outline, color: AppColors.blue),
              const SizedBox(width: 12),
              Expanded(
                child: Text(
                  'These are general recommendations. Consult your doctor or dietitian for personalized advice.',
                  style: AppTextStyles.caption(color: AppColors.blue),
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildRecommendedFood(String name, String benefit) {
    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16),
      ),
      child: Row(
        children: [
          Container(
            width: 40, height: 40,
            decoration: BoxDecoration(
              color: AppColors.sagePale,
              borderRadius: BorderRadius.circular(12),
            ),
            child: const Icon(Icons.check_circle, color: AppColors.sage, size: 20),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(name, style: AppTextStyles.body(weight: FontWeight.w500)),
                Text(benefit, style: AppTextStyles.caption()),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Future<void> _scanFood() async {
    try {
      final XFile? image = await _picker.pickImage(
        source: ImageSource.camera,
        imageQuality: 85, // compress slightly to stay under 10MB limit
      );
      if (image == null) return;

      setState(() => _isLoading = true);

      final bytes = await image.readAsBytes();
      final apiClient = ref.read(apiClientProvider);

      // Determine MIME type from file extension (camera always gives JPEG)
      final ext = image.name.split('.').last.toLowerCase();
      final mimeType = ext == 'png' ? 'image/png'
                     : ext == 'webp' ? 'image/webp'
                     : 'image/jpeg';

      final response = await apiClient.uploadFile(
        '/api/v1/food/scan',
        bytes,
        image.name,
        'file',
        fields: {'meal_type': _selectedMealType},  // required form field
        mimeType: mimeType,                         // fixes the 400: content_type was null
      );

      if (response != null && response['food_items'] != null) {
        final foods = List<Map<String, dynamic>>.from(response['food_items']);
        if (mounted) {
          setState(() => _scannedFoods = foods);
          // Auto-log immediately after scan succeeds
          if (foods.isNotEmpty) await _submitFoodLog();
        }
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Scan failed: $e')),
        );
      }
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  Future<void> _submitFoodLog() async {
    if (_scannedFoods.isEmpty) return;

    try {
      final apiClient = ref.read(apiClientProvider);
      await apiClient.post('/api/v1/food/log', body: {
        'meal_type': _selectedMealType,
        'food_items': _scannedFoods,
      });
      
      ref.invalidate(todayFoodLogsProvider);
      setState(() => _scannedFoods = []);
      
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Meal logged!')),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error: $e')),
        );
      }
    }
  }

  IconData _getMealIcon(String? type) {
    switch (type) {
      case 'breakfast': return Icons.wb_sunny_outlined;
      case 'lunch': return Icons.lunch_dining;
      case 'dinner': return Icons.dinner_dining;
      default: return Icons.fastfood_outlined;
    }
  }
}
