"""Offline packaging smoke tests; no root privileges or system installation."""
from pathlib import Path
import shutil
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/package_linux_deb.sh"


@pytest.mark.skipif(shutil.which("dpkg-deb") is None, reason="dpkg-deb not installed")
def test_package_and_validate_debian_structure(tmp_path):
    bundle = tmp_path / "bundle"
    (bundle / "lib").mkdir(parents=True)
    (bundle / "data" / "flutter_assets").mkdir(parents=True)
    entry = bundle / "goreecloud_metrics"
    entry.write_text("#!/bin/sh\nexit 0\n")
    entry.chmod(0o755)
    (bundle / "lib" / "libflutter_linux_gtk.so").write_bytes(b"mock-not-actual-shared-object")
    (bundle / "data" / "flutter_assets" / "AssetManifest.json").write_text("{}")
    output = tmp_path / "out"
    run = subprocess.run(["bash", str(SCRIPT), str(bundle), "0.1.0+1", str(output)],
                         capture_output=True, text=True, check=True, timeout=15)
    assert "Created" in run.stdout
    archive = output / "goreecloud-metrics_0.1.0+1_amd64.deb"
    assert archive.is_file() and (output / (archive.name + ".sha256")).is_file()
    metadata = subprocess.check_output(["dpkg-deb", "--field", str(archive)], text=True)
    listing = subprocess.check_output(["dpkg-deb", "--contents", str(archive)], text=True)
    assert "Package: goreecloud-metrics" in metadata
    assert "Architecture: amd64" in metadata
    assert "./usr/bin/goreecloud-metrics" in listing
    assert "./usr/share/applications/com.goreecloud.metrics.desktop" in listing
    assert "./opt/goreecloud/metrics/goreecloud_metrics" in listing
    existing = subprocess.run(["bash", str(SCRIPT), str(bundle), "0.1.0+1", str(output)],
                              capture_output=True, text=True, timeout=15)
    assert existing.returncode == 2
    assert "Refusing to overwrite" in existing.stderr


def test_rejects_nonrelease_payload_and_malicious_version(tmp_path):
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    for version in ("../../evil", "-1.0.0", "1.0/../x"):
        fail = subprocess.run(["bash", str(SCRIPT), str(bundle), version, str(tmp_path)],
                              capture_output=True, timeout=15)
        assert fail.returncode == 2
    incomplete = subprocess.run(["bash", str(SCRIPT), str(bundle), "0.1.0", str(tmp_path)],
                                capture_output=True, timeout=15)
    assert incomplete.returncode == 2
