import 'package:flutter/material.dart';

class AppColors {
  // Brand palette
  static const sage = Color(0xFF7FAF8C);
  static const sageLight = Color(0xFFC8DFCe);
  static const sagePale = Color(0xFFEFF6F1);
  static const blue = Color(0xFF6B9FBF);
  static const blueLight = Color(0xFFC5DDE8);
  static const bluePale = Color(0xFFEEF5FA);
  static const lavender = Color(0xFF9B8FB5);
  static const lavenderPale = Color(0xFFF0EDF6);
  static const warmWhite = Color(0xFFFAFAF7);
  static const cream = Color(0xFFF4F1EB);

  // Text
  static const textDark = Color(0xFF2C2C2A);
  static const textMid = Color(0xFF5A5A56);
  static const textLight = Color(0xFF909088);

  // Status (no hospital red)
  static const caution = Color(0xFFC0856B);
  static const cautionPale = Color(0xFFFBF3EE);

  // Dark (clinician dashboard)
  static const darkBg = Color(0xFF1C2437);
  static const darkCard = Color(0xFF242E42);
  static const darkBorder = Color(0xFF2E3B52);
}

class AppTextStyles {
  static const _fraunces = 'Fraunces';
  static const _dmSans = 'DMSans';

  static TextStyle display({double size = 36, FontWeight weight = FontWeight.w300, Color? color}) =>
      TextStyle(
        fontFamily: _fraunces,
        fontSize: size,
        fontWeight: weight,
        color: color ?? AppColors.textDark,
        height: 1.12,
        letterSpacing: -0.5,
      );

  static TextStyle heading({double size = 24, FontWeight weight = FontWeight.w400, Color? color}) =>
      TextStyle(
        fontFamily: _fraunces,
        fontSize: size,
        fontWeight: weight,
        color: color ?? AppColors.textDark,
        height: 1.2,
      );

  static TextStyle body({double size = 15, FontWeight weight = FontWeight.w400, Color? color}) =>
      TextStyle(
        fontFamily: _dmSans,
        fontSize: size,
        fontWeight: weight,
        color: color ?? AppColors.textDark,
        height: 1.6,
      );

  static TextStyle label({double size = 12, FontWeight weight = FontWeight.w500, Color? color}) =>
      TextStyle(
        fontFamily: _dmSans,
        fontSize: size,
        fontWeight: weight,
        color: color ?? AppColors.textLight,
        letterSpacing: 0.08,
      );

  static TextStyle caption({double size = 11, Color? color}) => TextStyle(
        fontFamily: _dmSans,
        fontSize: size,
        fontWeight: FontWeight.w400,
        color: color ?? AppColors.textLight,
        height: 1.4,
      );
}

class AppTheme {
  static ThemeData get lightTheme => _buildAppTheme();
}

ThemeData _buildAppTheme() {
  return ThemeData(
    useMaterial3: true,
    scaffoldBackgroundColor: AppColors.warmWhite,
    fontFamily: 'DMSans',
    colorScheme: ColorScheme.light(
      primary: AppColors.sage,
      secondary: AppColors.blue,
      tertiary: AppColors.lavender,
      surface: AppColors.warmWhite,
      error: AppColors.caution,
    ),
    appBarTheme: const AppBarTheme(
      backgroundColor: AppColors.warmWhite,
      elevation: 0,
      scrolledUnderElevation: 0.5,
      centerTitle: false,
      titleTextStyle: TextStyle(
        fontFamily: 'Fraunces',
        fontSize: 20,
        fontWeight: FontWeight.w400,
        color: AppColors.textDark,
      ),
      iconTheme: IconThemeData(color: AppColors.textMid),
    ),
    cardTheme: CardThemeData(
      elevation: 0,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
      color: Colors.white,
    ),
    sliderTheme: SliderThemeData(
      activeTrackColor: AppColors.sage,
      inactiveTrackColor: AppColors.sagePale,
      thumbColor: Colors.white,
      overlayColor: AppColors.sage.withValues(alpha: 0.1),
      thumbShape: const RoundSliderThumbShape(enabledThumbRadius: 14),
      trackHeight: 6,
    ),
    elevatedButtonTheme: ElevatedButtonThemeData(
      style: ElevatedButton.styleFrom(
        backgroundColor: AppColors.sage,
        foregroundColor: Colors.white,
        elevation: 0,
        padding: const EdgeInsets.symmetric(horizontal: 28, vertical: 16),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
        textStyle: AppTextStyles.body(weight: FontWeight.w500),
      ),
    ),
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: AppColors.cream,
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(14),
        borderSide: BorderSide.none,
      ),
      contentPadding: const EdgeInsets.symmetric(horizontal: 18, vertical: 16),
      hintStyle: AppTextStyles.body(color: AppColors.textLight),
    ),
    pageTransitionsTheme: const PageTransitionsTheme(
      builders: {
        TargetPlatform.android: CupertinoPageTransitionsBuilder(),
        TargetPlatform.iOS: CupertinoPageTransitionsBuilder(),
      },
    ),
  );
}
