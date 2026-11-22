# Security policy

## Supported versions

Security fixes are applied to the latest release on `main`. Older releases may not receive patches.

## Reporting a vulnerability

Do not open a public issue for a vulnerability. Send a private report to the repository owner with:

- Affected version and commit
- Reproduction steps
- Impact and required preconditions
- Suggested fix, if available

You will receive an acknowledgement and a remediation plan. Please allow time for a fix before public disclosure.

## Threat model

Paicode runs on a developer workstation with access to a project workspace, a model provider, and optionally local MCP servers and plugins. The primary risks are:

- A model or prompt injection attempting to escape the workspace
- A malicious dependency or plugin executing with user privileges
- Credential leakage through shell environments, logs, or telemetry
- Unreviewed shell commands mutating the host
- A compromised provider endpoint returning crafted tool calls

## Controls

- Workspace writes are confined to the project root with path resolution and sensitive-name denylists.
- On Linux, bubblewrap confines shell writes to the workspace, hides the home directory, and isolates package caches. Without bubblewrap, shell execution falls back to direct execution with command policy checks.
- Permission rules support `allow`, `ask`, and `deny` for shell, writes, MCP, plugins, reads, and host exploration.
- Approval prompts are required for `ask` rules in the terminal interface. Headless runs deny unapproved actions.
- Provider secrets, SSH agent sockets, and sensitive environment variables are removed from shell commands and hooks.
- MCP and plugins are opt-in. Read-only discussion and validation runs receive neither.
- Every mutation creates a local checkpoint before writing, and `/rewind` restores it.
- Token and cost budgets stop a run before the next request when a cap is crossed.
- Telemetry is disabled by default and never records prompts, file contents, or secrets.
- API keys and sessions are stored in a SQLite database with directory mode `0700` and file mode `0600`.
- The installer and package dependencies use exact version pins. Release artifacts include SHA256 checksums and a dependency inventory.

## Residual risks

- Shell policy is not a complete sandbox on platforms without bubblewrap.
- Plugins and MCP servers are trusted local code and can perform actions allowed by their own process.
- The local API has a single shared token and no per-user authorization.
- Model output is untrusted input and must not be treated as an authorization decision.
- Provider endpoints receive prompts and repository context. Review provider data handling before sending sensitive code.

## Hardening checklist

- Run in a container or disposable virtual machine for untrusted repositories.
- Keep `permission_mode` at `standard` or `strict`.
- Use `deny` rules for sensitive paths and destructive shell patterns.
- Do not mount host credential directories into containers.
- Enable telemetry only where local event files are acceptable.
- Review plugins and MCP server commands before enabling them.
