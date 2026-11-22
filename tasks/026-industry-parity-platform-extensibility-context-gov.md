---
id: "026"
title: "Industry parity platform: extensibility, context, governance, API, and release engineering"
type: "feature"
status: "in-progress"
created_at: "2026-11-22"
updated_at: "2026-11-22"
---

# [Feature] Industry parity platform: extensibility, context, governance, API, and release engineering

## Description
Raise Paicode from a strong local harness to an industry-grade platform. This task covers the capability gaps identified in the readiness audit: MCP, hooks and plugins, semantic context compaction, file checkpoints and rewind, permission policy and budgets, a local server API with SDK and web console, diagnostics, telemetry, release engineering, and a reproducible benchmark harness. No external product names may appear in source, docs, or commits.

## Phase 1: Configuration and policy foundation
- [ ] Unified global and project config loader with deterministic merge
- [ ] Permission rules with allow, ask, and deny effects
- [ ] Budget configuration for tokens and cost

## Phase 2: MCP
- [ ] Stdio MCP client with initialize, tools, resources, and prompts
- [ ] Remote MCP client over streamable HTTP
- [ ] MCP tool schemas injected into the tool registry
- [ ] MCP command and documentation

## Phase 3: Hooks and plugins
- [ ] Lifecycle hooks with JSON stdin, timeout, and deny exit code
- [ ] Local plugin loader with tool and hook registration
- [ ] Tool registry integration and tests

## Phase 4: Context and checkpoints
- [ ] Model-based conversation compaction with deterministic fallback
- [ ] File checkpoint store before every mutation
- [ ] Rewind CLI and TUI commands with tests

## Phase 5: Governance
- [ ] Policy enforcement for shell, writes, and MCP tools
- [ ] TUI approval flow for ask rules
- [ ] Token and cost budget enforcement
- [ ] Telemetry JSONL export

## Phase 6: Server, SDK, and web console
- [ ] Local HTTP API with token auth and SSE events
- [ ] Python SDK client
- [ ] Monochrome web console for sessions and prompts

## Phase 7: Release engineering and proof
- [ ] CI matrix, package build, checksums, and SBOM
- [ ] Benchmark harness for single versus team mode
- [ ] Security and enterprise documentation
- [ ] Full suite green, version bumped, all docs updated

## Context / Notes
- Target files: 
- Dependencies: None
