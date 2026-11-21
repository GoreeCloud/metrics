# CI action provenance and supply-chain guardrails

Every external action in the required GitHub CI workflow is pinned to the **full immutable Git commit SHA** instead of a mutable major-version tag. The source GitHub tag references were resolved using the authenticated GitHub API during the development interaction and each ref identified a commit, not an annotated tag; the major-version comment documents why it was selected.

| Action | Major tag | Verified SHA |
| --- | --- | --- |
| actions/checkout | v4 | 11d5960a326750d5838078e36cf38b85af677262 |
| actions/setup-python | v5 | a26af69be951a213d495a4c3e4e4022e16d87065 |
| actions/setup-node | v4 | 49933ea5288caeca8642d1e84afbd3f7d6820020 |
| actions/setup-java | v4 | cf277c60eb25467037889841efdb72551f06f6c3 |
| actions/upload-artifact | v4 | ea165f8d65b6e75b540449e92b4886f43607fa02 |
| subosito/flutter-action | v2 | 1a449444c387b1966244ae4d4f8c696479add0b2 |

The repository test rejects newly introduced floating action references. Dependabot proposals must be reviewed and retested through protected PRs, not auto-merged by passing a check alone. Pins reduce reference substitution risk but **do not** prove an action, its JavaScript dependencies, third-party packages, SDKs, build caches, Docker base image or app source are intrinsically safe. Flutter SDK stays pinned to 3.27.4 in CI and packages still require a separate vulnerability/license/provenance review before release.

No credentials, production access, signing keys or deployments are added by this change. The results of CI on the pinned action commits must be verified independently.
