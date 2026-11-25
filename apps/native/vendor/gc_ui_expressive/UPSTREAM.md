# GoreeCloud UI Flutter adapter — immutable source attribution

Canonical repository: https://github.com/GoreeCloud/gc-ui
Pinned upstream commit: `5ed3bf1e697a33ae603f086f782d3928e3758de6`
Canonical source path: `flutter/gc_ui_expressive/`
License: MIT (full `LICENSE` retained alongside this package).
Imported without modification: `pubspec.yaml`, `lib/goreecloud_ui_expressive.dart`,
`lib/src/generated/gc_ui_palettes.g.dart`, and `README.md`.

The native Metrics client owns the Lagoon selection and all app-specific views.
The existing generated `lib/gc_ui_colors.dart` and its offline generator remain
for pinned historical token verification; the official Flutter module now owns
the active app theme. No new telemetry, background collectors, credential stores
or network access are added. Updating the source requires a reviewed upstream
diff and passing Flutter analyze/test, Android and Linux builds. Real-device
visual/accessibility and release acceptance are independent.
