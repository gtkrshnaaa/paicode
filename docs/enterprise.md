# Enterprise deployment guide

Paicode is a local-first coding harness. Enterprise adoption depends on how it is deployed, how policy is distributed, and how usage is audited. This guide covers the supported controls and the remaining organizational responsibilities.

## Deployment models

- Developer workstation: install with the checksum-verified installer or a release artifact.
- Container: run the CLI or `pai serve` inside a hardened image with a read-only root filesystem and an explicit workspace mount.
- CI runner: use `pai run --json` and parse newline-delimited events. Keep the provider key in the CI secret store.
- Shared console: run `pai serve` behind an authenticating reverse proxy. Do not bind the server to a public interface without TLS and access control.

## Identity and access

The local API uses one bearer token per server process. Generate it from the secret store:

```bash
export PAICODE_SERVER_TOKEN="$(openssl rand -hex 32)"
pai serve --host 127.0.0.1 --port 8765
```

For team access, place the server behind an SSO-aware reverse proxy and keep the Paicode token private to the proxy. Built-in SSO and SCIM are not provided by the local server. Multi-tenant isolation requires one process, state directory, and container per tenant.

## Policy distribution

Project settings live in `.paicode/settings.json` and can be committed with the repository. Global settings live in `~/.config/paicode/settings.json`. Use configuration management to distribute a managed global file with:

- `permission_mode`: `standard` or `strict`
- `permissions`: deny rules for sensitive paths and destructive shell patterns
- `budget`: token and cost caps
- `telemetry`: local event recording policy
- `mcp` and `plugins`: explicit allowlists

A managed global file cannot override a project value with higher precedence. Review project settings before running untrusted repositories, or run them in a disposable container with an empty home directory.

## Audit and monitoring

Local audit data is stored in SQLite and, when enabled, JSONL telemetry:

- Sessions, transcripts, diffs, and usage in `paicode.db`
- Agent runs, contracts, ownership, findings, and strikes in the audit tables
- Tool and run events in `telemetry/events.jsonl`

Export a structured audit bundle with:

```bash
pai audit --out audit.json
```

The bundle contains sessions, agent runs, contracts, validation runs, and findings. Prompt text and file contents are not written to telemetry. Ship the bundle or state directory to the organization's logging platform. The schema is stable within a minor release.

## Data handling

Prompts and repository context are sent to the configured provider. Choose a provider and deployment region that match the organization's data policy. Paicode does not operate a hosted service and does not collect telemetry centrally. API keys are stored locally in SQLite with `0600` file permissions; they are not encrypted at rest beyond filesystem permissions.

## Supply chain

- Runtime dependencies are exactly pinned in `requirements.txt`.
- Release artifacts are built in CI and published with SHA256 checksums and an SBOM.
- The installer accepts `PAICODE_SHA256` to verify a downloaded source archive.
- Plugins and MCP servers are opt-in and execute with the user's privileges. Review them before enabling.
- The security policy is in [SECURITY.md](../SECURITY.md).

## Operations

- Health check: `GET /health`
- Version: `pai --version`
- Environment report: `pai doctor`
- Database reset with backup: `pai --reset-db`
- Backups: copy the SQLite database and the state directory while Paicode is stopped.

## Known boundaries

- Built-in SSO, SCIM, and role-based access control are not part of the local server.
- Windows native sandboxing is not implemented. Use WSL or a container.
- macOS uses direct execution unless an external sandbox is provided.
- Compliance certifications and support SLAs are organizational agreements, not code features.
- The local API is designed for a trusted workstation or a proxied team deployment, not direct public exposure.
