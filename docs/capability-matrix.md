# Coding Capability Matrix

Paicode is tested against real project fixtures with real compilers, interpreters, and test runners. The matrix is deterministic, runs without a provider key, and skips optional toolchains that are not installed.

Android application work is intentionally outside this matrix.

## Covered task classes

| Task class | Fixture | Verification |
| :--- | :--- | :--- |
| Python package and CLI | Calculator module, argparse CLI, `unittest` | `python3 -m unittest -q`, `compileall`, CLI output |
| Node package | ESM module, CLI, `node:test` suite | `npm test`, Node CLI output |
| C project | Header, source, test binary, `Makefile` | `make test` with `-Wall -Wextra -Werror` |
| C++ project | CMake project, C++20 source, assertion test | `cmake`, `cmake --build`, `ctest` |
| Java project | Single-file JVM program with assertions | `javac`, `java -ea` |
| Shell scripting | Backup script with functions, loops, and `set -euo pipefail` | Script execution, output, and filesystem result |
| JSON tooling | Configuration document | `jq` extraction and predicate checks |
| Git workflow | Repository, branch, commit, status, log | Real `git init`, `add`, `commit`, `switch`, `log` |
| SQLite data work | Schema, seed, join, aggregate report | Python `sqlite3` execution and query output |
| Backend and static web | JSON health endpoint, HTML page, HTTP client test | Loopback HTTP requests against a real server |
| Multi-file refactor | Rename a function across module, caller, and tests | `unittest` passes after surgical edits |
| Debugging loop | Failing statistic test | Failure is captured, source is fixed, rerun passes |
| Full agent loop | Scripted model writes, tests, reads failure, edits, finishes | Two shell runs, one failed and one green |

## Optional toolchains

These cases skip cleanly when the tool is absent:

- Go module with `go test ./...`
- Rust crate with `cargo test --quiet`
- TypeScript project with `tsc --noEmit`
- Docker image build and run, enabled with `PAICODE_TEST_DOCKER=1`

## Run the matrix

```bash
make matrix
```

The target covers `tests/coding`, the shell execution and sandbox suites, and the full agent coding loop.

## Shell execution

`bash` is a real bash shell. It supports pipes, redirection, environment variables, multi-command scripts, package managers, compilers, test runners, formatters, and git.

On Linux, Paicode uses bubblewrap when available:

- The workspace is mounted read-write.
- The rest of the filesystem is read-only.
- The real home directory is hidden and replaced with a private temporary home.
- Package caches are stored in an isolated cache directory.
- Child processes run in their own process group and are killed on timeout or stop.
- Output is bounded at 200,000 characters with an explicit truncation marker.

When bubblewrap is unavailable, Paicode falls back to direct execution. Provider secrets, SSH agent sockets, and sensitive environment variables are removed in both modes. Catastrophic host commands, privilege escalation, raw device writes, filesystem creation, package publishing, and privileged containers are rejected.

Environment controls:

```text
PAICODE_SHELL_SANDBOX=auto|direct|required
PAICODE_SANDBOX_CACHE=/path/to/cache
PAICODE_SANDBOX_NETWORK=0|1
PAICODE_SANDBOX_DOCKER=0|1
PAICODE_TEST_DOCKER=0|1
```
