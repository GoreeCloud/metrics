# Native GoreeCloud Metrics

Flutter app with **real Linux desktop** and **Android** targets, sharing application code under `lib/` and retaining generated native runners under `linux/` and `android/`. The application reads authenticated hub snapshots, per-host CPU history, current threshold indicators, read-only container snapshots and recent alert transitions. The latter two panels require the optional backend agent/worker and their APIs.

This is an early developer preview, not a signed or device-validated release. Requires Flutter SDK, compatible Android SDK/JDK or Linux desktop development libraries.

```bash
flutter pub get
flutter test
flutter run -d linux
flutter build apk --debug
```

Connect to an HTTPS hub on a trusted network, or localhost HTTP only during desktop development. Do not put administrator tokens into source control, command-line arguments or screenshots. Credentials are held only in app memory.

Design values reflect the provisional GoreeCloud UI alpha Lagoon theme.
