## SBOM attestations

The publisher generates an SPDX-2.3 SBOM for the digest-pinned tools image,
attests it with predicate type `https://spdx.dev/Document/v2.3`, and uploads
the artifact for 30 days. Its URL is recorded as `sbom_attestation` and
verified by the locked-image check when present; absence warns and continues.
# ADR-0018: Attest published tools images

## Status

Accepted

## Context

Digest-pinned image locks identify the published tools image but do not
prove which repository workflow built it.

## Decision

The publish workflow generates a GitHub build-provenance attestation for
the tools image and records its URL in the root and plugin digest locks.
The locked-image check verifies recorded provenance against the
`publish-ux-images.yml` workflow. Older pins without an attestation remain
usable and produce a warning until republished.

## Consequences

Publishing requires OIDC and attestation write permissions. The image
digest remains the execution pin; provenance adds verifiable build
metadata without changing the image reference.

## Launcher-side verification

`UX_VERIFY_ATTESTATION` accepts `auto` (the default), `require`, or `off`.
Before pulling a lock-provided image, and on every `prewarm`, the launcher
uses `gh attestation verify` with the lock entry and publisher workflow.
`auto` prints one note and skips for an image override, missing attestation,
missing `gh`, or failed `gh auth status`; once verification starts, failure
or timeout prevents the pull. `require` makes skip conditions errors, while
`off` never verifies. Ordinary invocations do not re-verify a locally
present image, and `--warn` doctor paths never verify.
