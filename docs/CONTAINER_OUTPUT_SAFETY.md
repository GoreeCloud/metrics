# Container CLI output boundary

Opt-in Podman/Docker container snapshots run an explicitly selected, locally resolved executable **without a shell**. Linux subprocess standard output is read in bounded chunks from a pipe, with an enforced maximum of 200,000 bytes and a six-second total deadline (startup, output and exit). The process is terminated if the limit is exceeded or the deadline expires, and diagnostic stderr is discarded rather than logged. Results still pass the strict field/name validation before entering host telemetry.

This prevents an overproducing container CLI from accumulating unlimited captured output in Python memory. The collector handles normal failures and nonzero provider exits without taking down the primary host metrics agent. No Docker daemon socket or container engine was activated as part of these source tests.

**Limits:** process-tree descendants may outlive the immediate CLI child, the Docker socket can convey root-equivalent permissions, stats provider versions vary, and CPU/memory figures depend on provider semantics. Enable this opt-in provider only after a least-privilege engine policy, trusted binary and real running-container readback. No production engine behavior is claimed.
