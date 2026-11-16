import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:fl_chart/fl_chart.dart';

import '../../../../core/theme/app_theme.dart';
import '../../../../core/di/providers.dart';

class TrendsPage extends ConsumerStatefulWidget {
  final String metric;

  const TrendsPage({super.key, required this.metric});

  @override
  ConsumerState<TrendsPage> createState() => _TrendsPageState();
}

class _TrendsPageState extends ConsumerState<TrendsPage> {
  late String _selectedMetric;
  int _selectedDays = 14;

  final List<Map<String, String>> _metrics = [
    {'key': 'pain', 'name': 'Pain', 'icon': 'healing'},
    {'key': 'fatigue', 'name': 'Fatigue', 'icon': 'bolt'},
    {'key': 'appetite', 'name': 'Appetite', 'icon': 'restaurant'},
    {'key': 'sleep', 'name': 'Sleep', 'icon': 'bedtime'},
    {'key': 'mood', 'name': 'Mood', 'icon': 'mood'},
  ];

  @override
  void initState() {
    super.initState();
    _selectedMetric = widget.metric;
  }

  IconData _getIcon(String iconName) {
    switch (iconName) {
      case 'healing':
        return Icons.healing_outlined;
      case 'bolt':
        return Icons.bolt_outlined;
      case 'restaurant':
        return Icons.restaurant_outlined;
      case 'bedtime':
        return Icons.bedtime_outlined;
      case 'mood':
        return Icons.mood_outlined;
      default:
        return Icons.show_chart;
    }
  }

  @override
  Widget build(BuildContext context) {
    final trendsAsync =
        ref.watch(trendsProvider((_selectedMetric, _selectedDays)));

    return Scaffold(
      appBar: AppBar(
        title: const Text('Recovery Trends'),
      ),
      body: Column(
        children: [
          // Metric selector
          SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
            child: Row(
              children: _metrics
                  .map((m) => Padding(
                        padding: const EdgeInsets.only(right: 8),
                        child: ChoiceChip(
                          label: Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              Icon(_getIcon(m['icon']!), size: 16),
                              const SizedBox(width: 4),
                              Text(m['name']!),
                            ],
                          ),
                          selected: _selectedMetric == m['key'],
                          onSelected: (_) =>
                              setState(() => _selectedMetric = m['key']!),
                          selectedColor: AppColors.sagePale,
                        ),
                      ))
                  .toList(),
            ),
          ),

          // Days selector
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 24),
            child: Row(
              children: [7, 14, 30]
                  .map((days) => Padding(
                        padding: const EdgeInsets.only(right: 8),
                        child: ChoiceChip(
                          label: Text('$days days'),
                          selected: _selectedDays == days,
                          onSelected: (_) =>
                              setState(() => _selectedDays = days),
                          selectedColor: AppColors.sagePale,
                        ),
                      ))
                  .toList(),
            ),
          ),

          const SizedBox(height: 24),

          // Chart
          Expanded(
            child: trendsAsync.when(
              data: (data) => _buildChart(data),
              loading: () => const Center(child: CircularProgressIndicator()),
              error: (_, __) =>
                  const Center(child: Text('Failed to load trends')),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildChart(Map<String, dynamic> data) {
    final dataPoints = data['data'] as List? ?? [];
    if (dataPoints.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.show_chart, size: 64, color: AppColors.textLight),
            const SizedBox(height: 16),
            Text('No data yet',
                style: AppTextStyles.body(color: AppColors.textMid)),
            const SizedBox(height: 8),
            Text('Complete your daily check-ins to see trends',
                style: AppTextStyles.caption()),
          ],
        ),
      );
    }

    // Convert data points to chart spots
    final actualSpots = <FlSpot>[];
    final expectedSpots = <FlSpot>[];

    for (int i = 0; i < dataPoints.length; i++) {
      final dp = dataPoints[i];
      if (dp['actual'] != null) {
        actualSpots.add(FlSpot(i.toDouble(), (dp['actual'] as num).toDouble()));
      }
      if (dp['expected'] != null) {
        expectedSpots
            .add(FlSpot(i.toDouble(), (dp['expected'] as num).toDouble()));
      }
    }

    final currentLevel = data['current_level'] ?? 0;

    return Padding(
      padding: const EdgeInsets.all(24),
      child: Column(
        children: [
          // Legend
          Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              _buildLegendItem('Your progress', AppColors.sage),
              const SizedBox(width: 24),
              if (expectedSpots.isNotEmpty)
                _buildLegendItem('Reference', AppColors.textLight),
            ],
          ),
          const SizedBox(height: 32),

          // Chart
          Expanded(
            child: LineChart(
              LineChartData(
                gridData: FlGridData(
                  show: true,
                  drawVerticalLine: false,
                  horizontalInterval: 2,
                  getDrawingHorizontalLine: (value) => FlLine(
                    color: AppColors.cream,
                    strokeWidth: 1,
                  ),
                ),
                titlesData: FlTitlesData(
                  leftTitles: AxisTitles(
                    sideTitles: SideTitles(
                      showTitles: true,
                      reservedSize: 30,
                      interval: 2,
                      getTitlesWidget: (value, meta) => Text(
                        value.toInt().toString(),
                        style: AppTextStyles.caption(),
                      ),
                    ),
                  ),
                  bottomTitles: const AxisTitles(
                      sideTitles: SideTitles(showTitles: false)),
                  topTitles: const AxisTitles(
                      sideTitles: SideTitles(showTitles: false)),
                  rightTitles: const AxisTitles(
                      sideTitles: SideTitles(showTitles: false)),
                ),
                borderData: FlBorderData(show: false),
                minY: 0,
                maxY: 10,
                lineBarsData: [
                  // Expected line
                  if (expectedSpots.isNotEmpty)
                    LineChartBarData(
                      spots: expectedSpots,
                      isCurved: true,
                      color: AppColors.textLight,
                      barWidth: 2,
                      isStrokeCapRound: true,
                      dotData: const FlDotData(show: false),
                      belowBarData: BarAreaData(show: false),
                    ),
                  // Actual line
                  if (actualSpots.isNotEmpty)
                    LineChartBarData(
                      spots: actualSpots,
                      isCurved: true,
                      color: AppColors.sage,
                      barWidth: 3,
                      isStrokeCapRound: true,
                      dotData: FlDotData(
                        show: true,
                        getDotPainter: (spot, percent, bar, index) =>
                            FlDotCirclePainter(
                          radius: 4,
                          color: AppColors.sage,
                          strokeWidth: 2,
                          strokeColor: Colors.white,
                        ),
                      ),
                      belowBarData: BarAreaData(
                        show: true,
                        color: AppColors.sagePale,
                      ),
                    ),
                ],
              ),
            ),
          ),

          // Status indicator
          if (currentLevel > 0) ...[
            const SizedBox(height: 16),
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: currentLevel == 3
                    ? AppColors.cautionPale
                    : (currentLevel == 2
                        ? AppColors.bluePale
                        : AppColors.sagePale),
                borderRadius: BorderRadius.circular(16),
              ),
              child: Row(
                children: [
                  Icon(
                    currentLevel >= 2 ? Icons.info_outline : Icons.trending_up,
                    color: currentLevel == 3
                        ? AppColors.caution
                        : (currentLevel == 2 ? AppColors.blue : AppColors.sage),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Text(
                      _getLevelMessage(currentLevel),
                      style: AppTextStyles.body(
                        color: currentLevel == 3
                            ? AppColors.caution
                            : (currentLevel == 2
                                ? AppColors.blue
                                : AppColors.sage),
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildLegendItem(String label, Color color) {
    return Row(
      children: [
        Container(
          width: 12,
          height: 12,
          decoration: BoxDecoration(
            color: color,
            shape: BoxShape.circle,
          ),
        ),
        const SizedBox(width: 4),
        Text(label, style: AppTextStyles.caption()),
      ],
    );
  }

  String _getLevelMessage(int level) {
    switch (level) {
      case 1:
        return 'Your recovery is slightly off track. Keep logging to monitor.';
      case 2:
        return 'We noticed a sustained deviation. Consider mentioning to your care team.';
      case 3:
        return 'Your care team has been notified. Please contact them if you have concerns.';
      default:
        return 'Your recovery is on track!';
    }
  }
}
