"""Guardrail: release APKs must not fall back to debug signing."""
from pathlib import Path


def test_android_release_signing_is_fail_closed():
    source = (Path(__file__).resolve().parents[1]
              / "apps/native/android/app/build.gradle").read_text()
    assert "GOREEMETRICS_ANDROID_KEYSTORE" in source
    assert "GOREEMETRICS_ANDROID_KEY_ALIAS" in source
    assert "GOREEMETRICS_ANDROID_STORE_PASSWORD" in source
    assert "GOREEMETRICS_ANDROID_KEY_PASSWORD" in source
    assert "releaseSigningReady" in source
    assert "throw new GradleException" in source
    assert "signingConfig = signingConfigs.debug" not in source
    assert "signingConfig signingConfigs.debug" not in source
    assert "signingConfig signingConfigs.release" in source


def test_secret_material_is_gitignored():
    source = (Path(__file__).resolve().parents[1] / ".gitignore").read_text()
    assert "*.jks" in source
    assert "*.keystore" in source
    assert "key.properties" in source
