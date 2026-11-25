# Android developer-build dependency caching

The five-check protected Metrics CI already uses an immutable-SHA-pinned actions/setup-java action and a cached Flutter SDK. The Android build now opts the **same pinned action** into Gradle dependency caching with cache keys derived from the checked-in Gradle settings, build files and wrapper properties.

This reduces unnecessary repeat Maven Central fetches after a successful first cache population. It is motivated by a **verified November 25, 2026** GitHub Actions Android failure in privacy-erasure PR #33: upstream Maven Central returned HTTP **429 Too Many Requests** fetching JavaWriter and ASM Gradle transitive dependencies. The failure was not diagnosed as a Metrics source compile error.

The cache cannot guarantee upstream availability, prevent all 429s, or prove artifact authenticity. The first clean build must fetch required dependencies, Gradle and Flutter version compatibility must remain tested, and GitHub Actions cache eligibility and eviction policies vary. Never disable dependency checks, bypass branch protection, or mark a failed job as green because an error appears transient.

No production APK, signing key, publishing action, release or deployed service is added. Required API, web, Flutter, Android and native Linux jobs remain in force.
