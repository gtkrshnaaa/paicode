# Local API and SDK

`pai serve` starts a token-protected HTTP server on `127.0.0.1:8765` by default. The same server hosts a monochrome web console at `/`.

```bash
pai serve
pai serve --host 127.0.0.1 --port 9000 --token "$PAICODE_SERVER_TOKEN"
```

If no token is provided, Paicode generates one and prints it at startup. Every API request requires `Authorization: Bearer <token>`. The console accepts the token in its header field and stores it in browser local storage.

Binding to a non-loopback interface exposes the API to the network. Use a token, TLS termination, and a trusted network. The server does not implement OAuth or multi-user isolation.

## Endpoints

| Method | Path | Purpose |
| :--- | :--- | :--- |
| GET | `/health` | Version and status |
| GET | `/api/sessions` | List sessions |
| POST | `/api/sessions` | Create a session with `workspace` and optional `title` |
| GET | `/api/sessions/{id}` | Session record, messages, transcript, diffs, and stats |
| POST | `/api/sessions/{id}/prompt` | Start a run with `prompt`, returns `run_id` |
| GET | `/api/runs/{id}/events` | Server-sent events for the run |

Server-sent events use the same typed objects as the terminal interface: `TextDelta`, `ToolStarted`, `ToolFinished`, `AgentPhase`, `AgentStatus`, `AgentAction`, `UsageUpdated`, `Finished`, and `ErrorEvent`.

## Python client

```python
from paicode.sdk import PaicodeClient

client = PaicodeClient("http://127.0.0.1:8765", "token")
print(client.health())
session = client.create_session("/work/project", "api demo")
run = client.prompt(session["id"], "Add a health check endpoint.")
print(client.events_url(run["run_id"]))
```

The client covers health, session listing, session creation, session detail, prompt submission, and event stream URLs. The raw HTTP API is stable enough for editor and CI integrations.
