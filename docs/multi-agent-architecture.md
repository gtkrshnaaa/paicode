# Multi-Agent Architecture

Paicode is multi-agent by default. Every feature request enters a 22-agent council before code is written. The council freezes a build contract, assigns one owner per file, and then active builders execute in parallel. An independent validator tests the integrated result and routes defects back to the owning builder until the work is clean or the repair budget is exhausted.

`--single-agent` remains available for small tasks. The default path is the 22-agent council.

## Roster

| Agent | Role |
| :--- | :--- |
| 1 | Lead architect, council chair, contract owner, arbiter |
| 2 | Frontend shell, routing, page composition |
| 3 | UI components and interaction states |
| 4 | Design system, layout, CSS tokens, responsiveness |
| 5 | Client state, forms, data flow, loading and error states |
| 6 | API client and request/response contracts |
| 7 | Backend HTTP handlers, routes, middleware |
| 8 | Domain services and business rules |
| 9 | Database schema, migrations, queries |
| 10 | Authentication, authorization, security |
| 11 | Validation, error handling, edge cases |
| 12 | Test architect, acceptance criteria, test matrix |
| 13 | Test implementer, fixtures, integration tests |
| 14 | Integration wiring and shared module boundaries |
| 15 | Accessibility, keyboard behavior, focus management |
| 16 | Performance, caching, bundle and query efficiency |
| 17 | DevOps, scripts, environment, build commands |
| 18 | Documentation and developer notes |
| 19 | Seed data, fixtures, local development data |
| 20 | Refactoring, naming, code quality, duplication |
| 21 | Observability, logging, failure diagnostics |
| 22 | Independent validator, tester, release gate |

Builder specialties are starting identities. The lead assigns work by file and domain. If a feature needs six builders, fourteen builders remain idle. If a feature needs more than 20 work units, the lead groups related files into bundles. One file never has two owners.

## Council protocol

A free-form 22-way chat is not used. The council is structured and auditable.

### Round 1: proposals

All 22 agents receive the user request, a compact repository snapshot, and their role. They respond in parallel with:

- Required files and modules.
- Interfaces that must be frozen.
- Test cases and acceptance criteria.
- Risks, edge cases, and ambiguities.
- What they will own and what they refuse to own.

Proposal calls run concurrently. The lead receives every proposal, including failed or timed-out roles when partial results are usable.

### Round 2: contract draft

The lead synthesizes the proposals into a build contract:

- Feature summary and acceptance criteria.
- Work units with owners.
- File ownership map.
- Function, class, and type signatures.
- API routes, payloads, and error shapes.
- Database schema and migration rules.
- DOM tree, components, props, state, and CSS tokens.
- Test plan and test file ownership.
- Build, lint, typecheck, and test commands.
- Shared files and freeze rules.
- Non-goals and risks.

The lead resolves conflicts. The contract is validated before review: at least one work unit, unique file owners, owners from agents 2 to 21, no more than 20 work units, and no file listed twice.

### Round 3: contract review

All 22 agents review the draft in parallel and return approve, approve with note, or objection with a concrete required change. The lead resolves objections and freezes contract version 1. Objections are normal council input, not errors; the chat shows one compact objection count while `/agents` keeps the per-agent verdict and required changes. No production file is written before this freeze.

## Build phase

The lead computes work units from the frozen contract. Only owners of active work units are activated. All active builders are submitted to the thread pool before any completion is collected, so they start together and do not take turns. The work phase reports the full active count immediately, each builder emits a running status with its owned files, and the diff report is flushed as one batch after the build. Completion times can differ because model latency differs, but the validator starts only after every builder has finished.

Each builder receives one brief:

- The frozen contract.
- Its exact file ownership list.
- Interfaces it must expose and consume.
- Test expectations.
- Commands it may run.
- Files it may read but not edit.
- Reporting format.
- Definition of done.

Builders use the file tools for source changes, so the write allowlist can enforce ownership. Shell commands are for builds, tests, formatters, and inspection. Unauthorized file changes are audited after the build.

## Parallelism and resource control

- One worker thread per active builder.
- A concurrency barrier test proves all active builders start before any completes.
- Model calls use a shared provider semaphore.
- Heavy shell commands use a separate build semaphore so 20 compilers do not overwhelm the host.
- Package installs and shared artifact directories use resource locks.
- Each agent gets a scratch directory and a cache namespace.
- Tests use unique ports, database files, and temporary directories.
- Provider requests share one key ring with locking and cooldowns.

## Validator and repair loop

Agent 22 is independent and read-only for production source. File tools deny writes, and sandboxed shell commands run on a disposable overlayfs workspace, so build and test artifacts are discarded when the command exits. It can read files, run the full test matrix, and write validation artifacts outside the workspace. It cannot silently fix production code.

Validation checks:

- Contract conformance.
- File ownership completeness.
- Full test suite.
- Acceptance tests.
- Build, lint, typecheck, and format commands.
- API request and response shapes.
- DOM and component contract.
- Database migration integrity.
- Secret leakage.
- Unauthorized file changes.
- Missing or skipped tests.

Findings are structured with severity, owner, file, line, failing command, expected result, actual result, reproduction steps, required fix, and required verification command.

The validator message is strict and direct. It is harsh about the defect and the accountability, never about the person. Slurs, personal abuse, and emojis are forbidden.

When validation passes, fails, or the run is stopped, agent 1 writes the final user-facing report. The report covers the summary, delivered files, validation result, defects, and next steps, and it streams into the chat as the lead message. If the report model call fails, a deterministic report is emitted. A stopped run uses the deterministic report without making another model call.

The owning builder fixes only its files, reruns scoped checks, and reports exact command output. The validator reruns full validation. Repeated identical defects earn a strike. After three strikes the lead reassigns the work or fixes it. After five validation rounds without a clean result, the run stops and reports the remaining findings.

## Persistence

SQLite migration 2 adds:

- `agent_runs`
- `agent_messages`
- `agent_tasks`
- `build_contracts`
- `file_ownership`
- `validation_runs`
- `validation_findings`
- `agent_strikes`
- `agent_events`

Each run stores session, phase, agent, role, status, timestamps, model, token usage, and error state. Contracts are stored as JSON and rendered Markdown. Findings and strikes are append-only audit records.

## TUI and CLI

- `pai` and `pai run` use multi-agent by default.
- `--single-agent` bypasses the council.
- `/agents` lists all 22 agents, phase, status, owned files, and strikes.
- `/contract` shows the frozen contract.
- `/bugs` shows current findings.
- The work bar shows `council 22/22`, `build 10/10`, and `validate round 1/5`.
- The chat shows lead summaries, phase changes, validation results, and final sign-off instead of 22 raw conversations.
- Cancellation stops all agents and kills sandboxed shell process groups.

## Tests

- Contract schema and ownership validation.
- 22 proposal calls and 22 contract reviews.
- Only needed builders activate.
- Concurrency barrier proves simultaneous start.
- Duplicate and missing owners are rejected.
- Unauthorized file edits are rejected.
- Validator finding routes to the correct owner.
- Repair loop reaches green.
- Three strikes and five-round termination.
- Cancellation and provider rate limit behavior.
- SQLite persistence and restart recovery.
- TUI agent status and `/agents`.
- `--single-agent` fallback.
- Full 22-agent fake-provider feature build.
- Live provider smoke test.

## Mandatory rule envelope

Every model request carries the full global and project `PAICODE.md` rules. This applies to single-agent turns, all 22 council proposals, lead synthesis, 22 contract reviews, lead arbitration, every builder turn, and every validator turn. The rule block is the first section of the prompt so provider prefix caching can reuse the repeated prefix. The previous 100,000 character rule truncation was removed, and per-file loading now allows up to 1,000,000 characters.

The audit test verifies that every fake-provider request contains a unique global rule marker. A live DeepSeek run with the real global rule file completed successfully, so mandatory rule injection does not break the workflow.

## Performance notes

Measured orchestration is not the bottleneck. The dominant cost is model latency and the mandatory rule tokens.

- The 22 council proposals and 22 contract reviews are dispatched concurrently.
- Active builders are dispatched concurrently, not in sequence.
- SQLite uses WAL, short-lived connections, and a busy timeout.
- Usage statistics are protected by a lock.
- The provider client has a shared concurrency gate, key cooldown, and retry backoff.
- The council, build, and validation phases write only small audit rows.
- A live 22-agent run at concurrency 6 completed in 373 seconds with 69 model requests and 1,337,818 total tokens while carrying the full 58 KB global rule file.
- With the default concurrency of 22, council and review phases have more headroom; lower the value only when the provider rate-limits or the host needs a ceiling.
- Full rules are intentionally repeated because the user requires them on every turn. Prefix caching is the correct optimization; dropping rules is not.

## Defaults

- Shared workspace with strict file ownership for version 1.
- Two full council rounds.
- Maximum 20 work units and 20 active builders.
- Builders start in parallel.
- Validator is read-only for production source and uses a disposable overlayfs workspace.
- Three strikes and five validation rounds.
- Multi-agent default for TUI and headless mode.
- `--single-agent` escape hatch.
- Every request carries the full PAICODE.md rule envelope.
- Same active model for every role by default. Per-role model overrides are optional.
