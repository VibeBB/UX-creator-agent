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
