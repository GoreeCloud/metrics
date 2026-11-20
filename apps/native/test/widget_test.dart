import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:goreecloud_metrics/main.dart';

void main() {
  testWidgets('native app opens with secure connect form', (tester) async {
    await tester.pumpWidget(const MetricsApp());
    expect(find.text('GoreeCloud Metrics'), findsOneWidget);
    expect(find.text('Connect to hub'), findsOneWidget);
    expect(find.byType(TextField), findsNWidgets(2));
  });
}
