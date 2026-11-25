"""CI Gradle cache contract for bounded Maven dependency retries."""
from pathlib import Path


def test_android_build_uses_pinned_setup_java_and_gradle_cache():
    root = Path(__file__).resolve().parents[1]
    ci = (root / ".github/workflows/ci.yml").read_text()
    android = ci.split("\n  android:", 1)[1].split("\n  linux:", 1)[0]
    assert "java-version: '17'" in android
    assert "cache: gradle" in android
    assert ("actions/setup-java@cf277c60eb25467037889841efdb72551f06f6c3"
            in android)
    assert "cache-dependency-path: |" in android
    for path in (
        "apps/native/android/gradle/wrapper/gradle-wrapper.properties",
        "apps/native/android/settings.gradle",
        "apps/native/android/build.gradle",
        "apps/native/android/app/build.gradle",
    ):
        assert path in android
        assert (root / path).is_file()
    assert "flutter build apk --debug" in android
    assert "cache: true" in android  # Existing Flutter SDK cache is distinct.
