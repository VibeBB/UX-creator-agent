# Security Policy

## Reporting a Vulnerability

Please report security vulnerabilities via the repository's private
security advisory channel (GitHub → Security → "Report a vulnerability").
Do not open public issues for security problems.

We aim to acknowledge reports within 7 days.

## Scope

UX-creator-agent runs UX tooling inside the `ghcr.io/vibebb/ux-tools`
container (`--network none`, non-root `ux` uid 1000, workspace bind-mount).
The plugin's hooks (`safety_rail`, `protect_generated`) enforce a denylist
of dangerous workspace writes; sibling imports are copy-in files verified
by sha256.

The agent never writes credentials, tokens, or secrets to artifacts or
logs; if you find a code path that could, that is a reportable defect.
