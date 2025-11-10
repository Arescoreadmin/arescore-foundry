# Arescore Foundry Security Posture

This document captures the defensive controls that ship with the current revision of Arescore Foundry and defines the operational workflows that keep them effective.

## Container hardening

- **Minimal bases** – All Python services build on top of the `python:3.12-slim` image (or `python:3.11-slim` where older runtimes are required) and install only their pinned runtime dependencies with `--no-cache-dir`.
- **Non-root users** – Runtime users are created for every service container. Ownership of application assets is transferred to the unprivileged account and `USER app` is enforced as the final instruction so the process cannot escalate back to root.
- **Deterministic builds** – Dockerfiles copy only the service-specific sources and generated stubs. Installing dependencies before switching to the non-root user keeps the final image immutable.

## Network egress controls

Two complementary approaches are provided:

1. **Kubernetes NetworkPolicies** – `infra/network/kubernetes/deny-all-egress.yaml` installs a namespace-wide default deny on egress traffic and adds explicit allow-lists for the orchestrator (to reach OPA and the revocation service) and for the revocation service (to reach DNS and the CRL distribution network). Update the placeholder CIDR with the authoritative CRL endpoints before applying.
2. **Container/host iptables script** – `infra/network/iptables/deny-egress.sh` can be executed during node bootstrap or from container init scripts to apply a deny-all egress stance using raw iptables rules. Allowed CIDRs and ports are injected through environment variables.

Together, the policies ensure workloads only reach the control plane and explicitly authorised external services.

## Runtime revocation pipeline

- **CRL-backed revocation service** – `services/revocation_service` continuously downloads the configured CRL, normalises the revoked runtime identifiers, and caches the results locally. It exposes health and revocation APIs for inspection and manual refreshes.
- **OPA data sync** – When fresh revocation data is ingested, the service pushes the snapshot to OPA's data API at `data/runtime_revocation_feed`. The policy package `foundry.runtime_revocation` consumes this feed and falls back to request-supplied revocation lists for backwards compatibility.
- **Observability** – Health endpoints report the last successful refresh, the current runtime count, and the most recent error state. These can be scraped by the existing telemetry pipeline.

## Supply-chain security

- **SBOM generation** – CI uses Anchore's Syft action to produce SPDX JSON SBOMs for each service image. Artifacts are uploaded for traceability.
- **CVE scanning** – Anchore's Grype action scans the same images and fails the build for HIGH or CRITICAL findings, preventing vulnerable containers from merging.

Generated SBOMs can be promoted to downstream governance tooling, while the Grype reports act as the enforcement gate.

## Incident response workflow

1. **Detection** – Alerts can originate from failed CI scans, revocation service health anomalies, or runtime monitoring (OPA denies, iptables logs).
2. **Triage** – Confirm whether the event is configuration drift (e.g., CRL endpoint outage) or an indicator of compromise (e.g., revoked runtime attempting execution).
3. **Containment** –
   - For compromised runtimes, add their identifiers to the CRL or manual allow-list file and trigger `POST /revocations/reload` to force immediate propagation.
   - For vulnerable containers, block merges until SBOM/CVE issues are remediated and regenerate images after dependency upgrades.
4. **Eradication & recovery** – Patch or redeploy affected services, verify the revocation service reports a successful refresh, and ensure OPA evaluations succeed with the updated data feed.
5. **Post-incident review** – Capture timelines and action items in the security wiki, update network policies or allow-lists as required, and add regression tests where feasible.

## Change management

- All security-affecting configuration (Dockerfiles, NetworkPolicies, CRL service) is version controlled and requires peer review.
- SBOM and scan artifacts are retained with CI run metadata for audit evidence.
- Operational overrides (e.g., temporary egress allow-lists) should be tracked via change tickets and reverted as soon as the underlying dependency is restored.
