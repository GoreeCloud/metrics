// GENERATED from canonical GoreeCloud/gc-ui alpha tokens. DO NOT EDIT.
// Immutable source commit: be8b819748d1ef0f6b2d3e786f4b22864cb3d07d
// Generator: scripts/generate_flutter_gc_ui.py
// License: MIT. Candidate values pending founder visual acceptance.
import 'package:flutter/material.dart';

@immutable
class GCUIColorRoles {
  final Color canvas;
  final Color surface;
  final Color surfaceTonal;
  final Color text;
  final Color textSoft;
  final Color outline;
  final Color outlineSoft;
  final Color positive;
  final Color onPositive;
  final Color warning;
  final Color onWarning;
  final Color negative;
  final Color onNegative;
  final Color focusRing;
  final Color brand;
  final Color onBrand;
  final Color brandContainer;
  final Color onBrandContainer;

  const GCUIColorRoles({
    required this.canvas,
    required this.surface,
    required this.surfaceTonal,
    required this.text,
    required this.textSoft,
    required this.outline,
    required this.outlineSoft,
    required this.positive,
    required this.onPositive,
    required this.warning,
    required this.onWarning,
    required this.negative,
    required this.onNegative,
    required this.focusRing,
    required this.brand,
    required this.onBrand,
    required this.brandContainer,
    required this.onBrandContainer,
  });
}

abstract final class GoreeCloudUIColors {
  static const double radiusMedium = 18.0;

  static const GCUIColorRoles light = GCUIColorRoles(
    canvas: Color(0xFFF6F7FB),
    surface: Color(0xFFFFFFFF),
    surfaceTonal: Color(0xFFEEF0F7),
    text: Color(0xFF1B2030),
    textSoft: Color(0xFF505B70),
    outline: Color(0xFF68758C),
    outlineSoft: Color(0xFFCED3DF),
    positive: Color(0xFF166B4B),
    onPositive: Color(0xFFFFFFFF),
    warning: Color(0xFF955000),
    onWarning: Color(0xFFFFFFFF),
    negative: Color(0xFFB3261E),
    onNegative: Color(0xFFFFFFFF),
    focusRing: Color(0xFF2346CA),
    brand: Color(0xFF00697A),
    onBrand: Color(0xFFFFFFFF),
    brandContainer: Color(0xFFC4F2F4),
    onBrandContainer: Color(0xFF064D58),
  );

  static const GCUIColorRoles dark = GCUIColorRoles(
    canvas: Color(0xFF0D121D),
    surface: Color(0xFF171D2A),
    surfaceTonal: Color(0xFF252D3D),
    text: Color(0xFFF2F4FB),
    textSoft: Color(0xFFCED5E5),
    outline: Color(0xFF9CA8BC),
    outlineSoft: Color(0xFF505B70),
    positive: Color(0xFF95E0BB),
    onPositive: Color(0xFF0D271D),
    warning: Color(0xFFFFCE83),
    onWarning: Color(0xFF332000),
    negative: Color(0xFFFFB4AB),
    onNegative: Color(0xFF4F1410),
    focusRing: Color(0xFFBFCBFF),
    brand: Color(0xFF8BE7F1),
    onBrand: Color(0xFF003A42),
    brandContainer: Color(0xFF19525B),
    onBrandContainer: Color(0xFFD7FAFF),
  );

  static GCUIColorRoles forBrightness(Brightness brightness) =>
      brightness == Brightness.dark ? dark : light;
}
