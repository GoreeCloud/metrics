# GoreeCloud UI — native Flutter theme adoption

The Flutter Linux Desktop and Android clients now read **generated Dart color roles** from an immutable snapshot of the canonical GoreeCloud UI source:

- Upstream: https://github.com/GoreeCloud/gc-ui
- Immutable source revision: be8b819748d1ef0f6b2d3e786f4b22864cb3d07d
- Canonical source path: tokens/gc.tokens.json
- Snapshot SHA256: d3226033ba50d601fcabbb01eadc2fdff8eb1be6cde6f6ebe8b0b47f1041e8e0
- License: MIT (tracked as an internal design source and independently attributed in THIRD_PARTY_NOTICES.md)
- Accent: Lagoon. Light and dark semantic surfaces, text, brand, error and outline roles are preserved without invented hex values.

The offline deterministic generator is scripts/generate_flutter_gc_ui.py. It fails closed if the source snapshot is altered without review; its input and provenance are retained under apps/native/design/. The Dart output apps/native/lib/gc_ui_colors.dart is generated and must not be manually edited. To verify it:

~~~sh
python3 scripts/generate_flutter_gc_ui.py --check
cd apps/native
flutter analyze
flutter test
~~~

To regenerate intentionally after reviewing/updating the source revision and checksum, the authorized developer can run the generator with --write and commit the validated results together with the provenance. Retain previous revision for rollback.

**Status:** GoreeCloud UI itself labels these values as **alpha candidate values**, pending founder visual acceptance. This work adopts tokens, not the entire native component system. Flutter Material 3 remains the UI foundation, with the canonical Lagoon palette supplying semantic colors. Android Material 3 Expressive behaviors and full GoreeCloud UI native component integration remain separate acceptance tasks; do not mark either as fully shipped. Real Linux desktop and physical Android appearance, contrast, accessibility, density and motion verification remain required.
