import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:goreecloud_ui_expressive/goreecloud_ui_expressive.dart';

void main() {
  testWidgets('Metrics uses canonical Lagoon light and dark palettes', (tester) async {
    for (final brightness in [Brightness.light, Brightness.dark]) {
      final theme = GoreeCloudFlutterTheme.build(
        brightness: brightness,
        accent: GoreeAccent.lagoon,
      );
      final palette = GoreeCloudPalette.forAppearance(
        brightness: brightness,
        accent: GoreeAccent.lagoon,
      );
      expect(theme.useMaterial3, true);
      expect(theme.scaffoldBackgroundColor, palette.canvas);
      expect(theme.colorScheme.primary, palette.brand);
      expect(theme.colorScheme.onSurface, palette.text);
    }
  });
}
