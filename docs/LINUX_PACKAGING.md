# Linux desktop Debian package (developer preview)

GoreeCloud Metrics uses **Flutter Linux Desktop** as the approved primary Linux UI framework. The GitHub Actions Linux build can package the verified Flutter release bundle into a Debian-format amd64 .deb for review; this does **not** install it, publish it as a Stable release, or establish runtime acceptance.

Prerequisites for a local developer build: the existing Flutter Linux desktop SDK, CMake, Ninja, GTK development headers, and dpkg-deb on an authorized Linux x64 host. Build the Flutter bundle first, then package it using an explicit version string from the tracked pubspec file:

~~~sh
cd apps/native
flutter build linux --release
cd ../..
version=$(sed -n 's/^version: //p' apps/native/pubspec.yaml | head -n 1)
bash scripts/package_linux_deb.sh apps/native/build/linux/x64/release/bundle "$version" artifacts
dpkg-deb --info artifacts/goreecloud-metrics_"$version"_amd64.deb
dpkg-deb --contents artifacts/goreecloud-metrics_"$version"_amd64.deb
(cd artifacts && sha256sum -c "goreecloud-metrics_${version}_amd64.deb.sha256")
~~~

The packager runs without root, requires an existing complete release bundle, checks for unexpected symlinks and setuid files, refuses to overwrite package filenames, creates an owner-independent Debian archive and SHA-256 checksum, and includes a launcher and .desktop entry with a standard system-monitor icon fallback. It does **not** install the package or enroll the machine in any telemetry collection. Package dependencies are declared for GTK, Glib, libc and C++; validate them on each supported Debian/Ubuntu release.

**Limitations:** no GPG or repository signing, update channel, rollback/upgrade or sandbox acceptance, verified host library compatibility, real GUI runtime/accessibility test, package-signature verification, or actual installation on a target host. Consider a Flatpak sandbox only after source, permissions and runtime acceptance are established. The CI artifact is an unsigned test installer, not a published release.
