# Android release-signing policy

**Development status:** CI builds only a debug APK for automated qualification. A debug APK is not a production-signed release, and publishing a release is not automated.

The application previously inherited Flutter's generated Gradle template that signed the Android *release* build using a **debug key**. The release build now **fails closed** if an explicitly configured, existing external release keystore and all four signing environment variables are absent. Ordinary debug builds do not require any signing secrets.

Before deliberately building a release, obtain an authorized signing key through an approved secure process, store it **outside** the repository and backup/restore it separately. Set these four variables in a private terminal or ephemeral authorized CI secret context:

~~~sh
GOREEMETRICS_ANDROID_KEYSTORE=/absolute/private/location/release.jks
GOREEMETRICS_ANDROID_KEY_ALIAS=your-private-key-alias
GOREEMETRICS_ANDROID_STORE_PASSWORD=read-from-your-secret-manager
GOREEMETRICS_ANDROID_KEY_PASSWORD=read-from-your-secret-manager
~~~

Do not put actual values in source, shell history, docs, GitHub Actions outputs, screenshots or logs. The Gradle release task requires a regular file at the absolute keystore location, outside the source tree, and all four non-empty values. It refuses missing configuration, replacing debug-key release signing with an explicit operator-only signing gate.

After approval, run `flutter build apk --release` from `apps/native` and verify the APK signature using Android SDK `apksigner verify --verbose --print-certs <apk>`, manually comparing the signing certificate fingerprint against the expected independently recorded release signing identity. Validate ABI, target SDK, app ID, app permissions, security posture, and physical-device install/update behavior **before** considering any release. Keep certificate fingerprints and artifact checksums as release acceptance evidence without revealing private-key material.

**Not accomplished by this change:** generating signing keys, managing their backups, trusted release signing, signing an APK, publishing a release, APK delivery to `GoreeCloud/Artifacts/`, or physical-device acceptance. The repository's debug APK build remains a development artifact only.
