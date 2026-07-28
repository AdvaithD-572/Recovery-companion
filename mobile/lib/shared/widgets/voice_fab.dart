import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../../core/theme/app_theme.dart';

/// Floating voice button — bottom-left on every main screen
class VoiceFab extends StatefulWidget {
  const VoiceFab({super.key});

  @override
  State<VoiceFab> createState() => _VoiceFabState();
}

class _VoiceFabState extends State<VoiceFab> with SingleTickerProviderStateMixin {
  late AnimationController _ctrl;
  late Animation<double> _scaleAnim;

  @override
  void initState() {
    super.initState();
    _ctrl = AnimationController(vsync: this, duration: const Duration(milliseconds: 150));
    _scaleAnim = Tween<double>(begin: 1.0, end: 0.92).animate(
      CurvedAnimation(parent: _ctrl, curve: Curves.easeOut),
    );
  }

  @override
  void dispose() {
    _ctrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Positioned(
      bottom: 28,
      left: 24,
      child: GestureDetector(
        onTapDown: (_) => _ctrl.forward(),
        onTapUp: (_) async {
          await _ctrl.reverse();
          if (context.mounted) context.push('/voice');
        },
        onTapCancel: () => _ctrl.reverse(),
        child: ScaleTransition(
          scale: _scaleAnim,
          child: Container(
            width: 56,
            height: 56,
            decoration: BoxDecoration(
              gradient: const LinearGradient(
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
                colors: [AppColors.sage, AppColors.blue],
              ),
              shape: BoxShape.circle,
              boxShadow: [
                BoxShadow(
                  color: AppColors.blue.withValues(alpha: 0.4),
                  blurRadius: 16,
                  offset: const Offset(0, 6),
                ),
              ],
            ),
            child: const Icon(Icons.mic_rounded, color: Colors.white, size: 24),
          ),
        ),
      ),
    );
  }
}

/// Soft info card used throughout the app
class InfoCard extends StatelessWidget {
  final Widget child;
  final Color? backgroundColor;
  final EdgeInsets? padding;
  final VoidCallback? onTap;
  final Border? border;

  const InfoCard({
    super.key,
    required this.child,
    this.backgroundColor,
    this.padding,
    this.onTap,
    this.border,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 150),
        decoration: BoxDecoration(
          color: backgroundColor ?? Colors.white,
          borderRadius: BorderRadius.circular(20),
          border: border,
          boxShadow: const [
            BoxShadow(color: Color(0x08000000), blurRadius: 12, offset: Offset(0, 4)),
          ],
        ),
        padding: padding ?? const EdgeInsets.all(18),
        child: child,
      ),
    );
  }
}

/// Gradient avatar placeholder
class PatientAvatar extends StatelessWidget {
  final String? name;
  final double size;

  const PatientAvatar({super.key, this.name, this.size = 40});

  @override
  Widget build(BuildContext context) {
    final initials = name != null
        ? name!.split(' ').take(2).map((w) => w.isNotEmpty ? w[0] : '').join().toUpperCase()
        : '?';

    return Container(
      width: size, height: size,
      decoration: const BoxDecoration(
        shape: BoxShape.circle,
        gradient: LinearGradient(
          colors: [AppColors.sage, AppColors.blue],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
      ),
      child: Center(
        child: Text(
          initials,
          style: TextStyle(
            color: Colors.white,
            fontSize: size * 0.38,
            fontWeight: FontWeight.w600,
            fontFamily: 'DMSans',
          ),
        ),
      ),
    );
  }
}

/// Escalation level badge
class EscalationBadge extends StatelessWidget {
  final int level;
  const EscalationBadge({super.key, required this.level});

  @override
  Widget build(BuildContext context) {
    final configs = {
      0: (AppColors.sagePale, AppColors.sage, 'Normal'),
      1: (AppColors.bluePale, AppColors.blue, 'Slight deviation'),
      2: (AppColors.lavenderPale, AppColors.lavender, 'Needs attention'),
      3: (AppColors.cautionPale, AppColors.caution, 'Review needed'),
    };
    final (bg, fg, label) = configs[level] ?? (AppColors.sagePale, AppColors.sage, 'Normal');

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(
        color: bg,
        borderRadius: BorderRadius.circular(99),
      ),
      child: Text(
        label,
        style: TextStyle(
          color: fg,
          fontSize: 11,
          fontWeight: FontWeight.w600,
          fontFamily: 'DMSans',
        ),
      ),
    );
  }
}
