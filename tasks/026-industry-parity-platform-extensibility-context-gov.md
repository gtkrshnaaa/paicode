---
id: "026"
title: "Industry parity platform: extensibility, context, governance, API, and release engineering"
type: "feature"
status: "done"
created_at: "2026-11-22"
updated_at: "2026-11-22"
---

# [Feature] Industry parity platform: extensibility, context, governance, API, and release engineering

## Description
Raise Paicode from a strong local harness to an industry-grade platform. This task covers the capability gaps identified in the readiness audit: MCP, hooks and plugins, semantic context compaction, file checkpoints and rewind, permission policy and budgets, a local server API with SDK and web console, diagnostics, telemetry, release engineering, and a reproducible benchmark harness. No external product names may appear in source, docs, or commits.

## Phase 1: Configuration and policy foundation
- [x] Unified global and project config loader with deterministic merge
- [x] Permission rules with allow, ask, and deny effects
- [x] Budget configuration for tokens and cost

## Phase 2: MCP
- [x] Stdio MCP client with initialize, tools, resources, and prompts
- [x] Remote MCP client over streamable HTTP
- [x] MCP tool schemas injected into the tool registry
- [x] MCP command and documentation

## Phase 3: Hooks and plugins
- [x] Lifecycle hooks with JSON stdin, timeout, and deny exit code
- [x] Local plugin loader with tool and hook registration
- [x] Tool registry integration and tests

## Phase 4: Context and checkpoints
- [x] Model-based conversation compaction with deterministic fallback
- [x] File checkpoint store before every mutation
- [x] Rewind CLI and TUI commands with tests

## Phase 5: Governance
- [x] Policy enforcement for shell, writes, and MCP tools
- [x] TUI approval flow for ask rules
- [x] Token and cost budget enforcement
- [x] Telemetry JSONL export

## Phase 6: Server, SDK, and web console
- [x] Local HTTP API with token auth and SSE events
- [x] Python SDK client
- [x] Monochrome web console for sessions and prompts

## Phase 7: Release engineering and proof
- [x] CI matrix, package build, checksums, and SBOM
- [x] Benchmark harness for single versus team mode
- [x] Security and enterprise documentation
- [x] Full suite green, version bumped, all docs updated

## Context / Notes
- Target files: 
- Dependencies: None
