#!/usr/bin/env bash
# Package an already-built Flutter Linux x64 bundle, without installing it.
set -euo pipefail
if [[ "$#" -ne 3 ]]; then
  echo "Usage: bash scripts/package_linux_deb.sh <bundle-dir> <version> <output-dir>" >&2
  exit 2
fi
bundle=$1
version=$2
output_dir=$3
if [[ ! "$version" =~ ^[0-9][0-9A-Za-z.+~-]*$ ]]; then
  echo "Refusing unsafe Debian version string" >&2
  exit 2
fi
if [[ ! -d "$bundle" || ! -f "$bundle/goreecloud_metrics" || ! -x "$bundle/goreecloud_metrics" ||
      ! -f "$bundle/lib/libflutter_linux_gtk.so" || ! -d "$bundle/data/flutter_assets" ]]; then
  echo "Expected Flutter Linux x64 RELEASE bundle is missing required runtime files" >&2
  exit 2
fi
if find "$bundle" -type l -print -quit | grep -q .; then
  echo "Refusing external or ambiguous symlinks in the Flutter bundle" >&2
  exit 2
fi
command -v dpkg-deb >/dev/null || { echo "dpkg-deb is required" >&2; exit 2; }
mkdir -p "$output_dir"
output_dir=$(realpath "$output_dir")
target="$output_dir/goreecloud-metrics_${version}_amd64.deb"
if [[ -e "$target" || -L "$target" ]]; then
  echo "Refusing to overwrite existing Debian package" >&2
  exit 2
fi
stage=$(mktemp -d "${TMPDIR:-/tmp}/gc-metrics-deb.XXXXXXXX")
cleanup() { if [[ -n "${stage:-}" && -d "$stage" ]]; then rm -rf -- "$stage"; fi; }
trap cleanup EXIT
mkdir -p "$stage/DEBIAN" "$stage/opt/goreecloud/metrics" "$stage/usr/bin" "$stage/usr/share/applications"
cp -a -- "$bundle/." "$stage/opt/goreecloud/metrics/"
cat > "$stage/DEBIAN/control" <<EOF
Package: goreecloud-metrics
Version: ${version}
Section: admin
Priority: optional
Architecture: amd64
Maintainer: GoreeCloud <admin@goreecloud.com>
Depends: libc6, libstdc++6, libgtk-3-0 | libgtk-3-0t64, libglib2.0-0 | libglib2.0-0t64
Description: GoreeCloud Metrics native Flutter desktop monitoring client
 Open-source development preview of a self-hosted metrics dashboard.
 This package does not install or enable a monitoring agent or hub.
EOF
cat > "$stage/usr/bin/goreecloud-metrics" <<'EOF'
#!/bin/sh
exec /opt/goreecloud/metrics/goreecloud_metrics "$@"
EOF
chmod 0755 "$stage/usr/bin/goreecloud-metrics"
cat > "$stage/usr/share/applications/com.goreecloud.metrics.desktop" <<'EOF'
[Desktop Entry]
Type=Application
Name=GoreeCloud Metrics
Comment=View private host and container telemetry
Exec=goreecloud-metrics
Icon=utilities-system-monitor
Categories=System;Monitor;
Terminal=false
EOF
# Package data files have no executable write permissions or setuid bit.
if find "$stage" -perm /6000 -print -quit | grep -q .; then
  echo "Refusing setuid/setgid files in package tree" >&2
  exit 2
fi
dpkg-deb --root-owner-group --build "$stage" "$target" >/dev/null
(cd "$output_dir" && sha256sum -- "$(basename "$target")" > "$(basename "$target").sha256")
printf 'Created %s\n' "$target"
printf 'SHA-256 checksum %s\n' "$target.sha256"
