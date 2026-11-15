# C2 post-merge CI audit

These snapshots query each immutable merge commit, rather than a moving
`main` branch. The [machine-readable record](post-merge-ci-validation.json)
preserves full revisions, capture times, job IDs and private snapshot hashes.
Raw API/tool output remains private.

| Repository / PR | Merge revision | Passed | Failed | Pending | Skipped |
| --- | --- | ---: | ---: | ---: | ---: |
| [VibeBB/UX-creator-agent #190](https://github.com/VibeBB/UX-creator-agent/pull/190) | [514673b4](https://github.com/VibeBB/UX-creator-agent/commit/514673b4d38018d7787f662338b6c03aa1108884/checks) | 16 | 0 | 0 | 1 |
| [VibeBB/bard-agent #200](https://github.com/VibeBB/bard-agent/pull/200) | [54585e94](https://github.com/VibeBB/bard-agent/commit/54585e9422c391f93c2571616ad1742f1579f372/checks) | 15 | 0 | 0 | 2 |
| [VibeBB/dashboard-agent #252](https://github.com/VibeBB/dashboard-agent/pull/252) | [30d499d8](https://github.com/VibeBB/dashboard-agent/commit/30d499d8b8f5274f494b8e03423b4a56e1a7c5c8/checks) | 19 | 0 | 0 | 1 |
| [VibeBB/document-agent #65](https://github.com/VibeBB/document-agent/pull/65) | [e1aff38c](https://github.com/VibeBB/document-agent/commit/e1aff38c15060e0739bec376cb378309966b1a5e/checks) | 10 | 0 | 0 | 1 |
| [VibeBB/electrical-circuit-agent #358](https://github.com/VibeBB/electrical-circuit-agent/pull/358) | [9c2b956c](https://github.com/VibeBB/electrical-circuit-agent/commit/9c2b956c1b17c0381bb03ddcadf72bcfe3971c50/checks) | 35 | 0 | 0 | 1 |
| [VibeBB/firmware-agent #160](https://github.com/VibeBB/firmware-agent/pull/160) | [7ff6c32c](https://github.com/VibeBB/firmware-agent/commit/7ff6c32cdd0864ae615c16016125ecad1a638857/checks) | 19 | 0 | 1 | 1 |
| [VibeBB/fpga-agent #157](https://github.com/VibeBB/fpga-agent/pull/157) | [7ddab6cf](https://github.com/VibeBB/fpga-agent/commit/7ddab6cfd59a18385d465035df965cb062e567d3/checks) | 14 | 0 | 0 | 2 |
| [VibeBB/mechanical-agent #265](https://github.com/VibeBB/mechanical-agent/pull/265) | [85e7b1ae](https://github.com/VibeBB/mechanical-agent/commit/85e7b1aea7bb1ff0fcc9cc6ab0fd79444fc7ea6b/checks) | 12 | 0 | 0 | 1 |
| [VibeBB/production-engineering-agent #185](https://github.com/VibeBB/production-engineering-agent/pull/185) | [acd3380b](https://github.com/VibeBB/production-engineering-agent/commit/acd3380b167405cfd35ace20b64effb422839f23/checks) | 13 | 0 | 0 | 2 |
| [VibeBB/simulation-agent #154](https://github.com/VibeBB/simulation-agent/pull/154) | [d5239440](https://github.com/VibeBB/simulation-agent/commit/d52394409284805c122e0d084cfa6e1852f2ded1/checks) | 15 | 0 | 0 | 1 |
| [VibeBB/wire-agent #261](https://github.com/VibeBB/wire-agent/pull/261) | [64033c40](https://github.com/VibeBB/wire-agent/commit/64033c40bf8bfdb6fdfcab4fcf8d4bba586134a7/checks) | 16 | 0 | 0 | 1 |

The captured checks report 184 successes, 0
failures, 1 pending job and 14 skipped jobs.
Firmware's [tools-image publication](https://github.com/VibeBB/firmware-agent/actions/runs/43712338143/job/132815455575)
was still building. Its publication and new image installation remain
unverified. No job was rerun, cancelled or bypassed for this audit.

These are scoped workflow conclusions. They do not prove release-install
compatibility, provider perception, GUI quality, real audio, hardware or
product acceptance. The remaining release/feature matrix in the
[implementation plan](implementation-plan.md) still applies.
