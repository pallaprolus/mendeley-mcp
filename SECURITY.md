# Security Policy

This MCP server handles Mendeley OAuth credentials (client secret, access and
refresh tokens) and downloads files via pre-signed URLs. Reports about
credential handling, token exposure, or unsafe request behavior are
particularly relevant.

## Supported versions

Only the latest release receives security fixes.

| Version | Supported |
| ------- | --------- |
| latest (0.3.x) | yes |
| older | no — please upgrade |

## Reporting a vulnerability

**Please do not open a public issue for security reports.**

Use GitHub's private vulnerability reporting:
[Report a vulnerability](https://github.com/pallaprolus/mendeley-mcp/security/advisories/new).

This is a solo-maintained project, so commitments are deliberately modest:

- You will get an acknowledgment within **7 days** (best effort).
- Confirmed vulnerabilities are fixed in the next release, prioritized over
  feature work, and disclosed in the release notes once a fix is available.
- Credit is given to reporters in the advisory and release notes unless you
  ask otherwise.

## Out of scope

- Vulnerabilities in the Mendeley API itself (report to
  [Elsevier](https://www.elsevier.com/about/policies-and-standards/responsible-disclosure))
- Issues requiring physical access to a machine where credentials are already
  stored in the OS keychain
