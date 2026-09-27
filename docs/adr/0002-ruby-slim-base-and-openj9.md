# ADR-0002: ruby:*-slim base image and Semeru OpenJ9 JRE

- Status: Accepted
- Date: 2026-09-26

## Context

The tools image needs Ruby 4, Chromium (mermaid-cli), a JRE (PlantUML),
mruby built from source, and the sibling repos' standard Debian toolchain.
An alpine base would save ~126 MB but forces musl workarounds for
Chromium, the JVM, and mruby's build.

## Decision

`FROM ruby:4.0.7-slim-trixie` pinned by digest — Debian 13 with the
official Ruby 4.0.7 build — keeping apt, font, non-root-user, and CI
patterns identical to the siblings.

The JRE is **IBM Semeru OpenJ9 27.0.0.0** installed to `/opt/jre`
verbatim from electrical-circuit-agent's circuit-tools Dockerfile
(sha256-verified tarball, `JAVA_HOME=/opt/jre`, OpenJ9 and version greps
in the build smoke). Debian's `nodejs`/`npm` (LTS in trixie) provides the
mermaid-cli runtime; Chromium is the Debian `chromium` package driven via
a committed `docker/puppeteer-config.json` (`--no-sandbox`).

## Consequences

- Image is ~1 GB class; acceptable because it matches sibling images.
- Every third-party component is sha256- or apt-pinned and recorded in
  THIRD_PARTY_NOTICES.md.
