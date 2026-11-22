import json
import secrets
import threading
from dataclasses import asdict, dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from uuid import uuid4

from .. import __version__
from ..agent.events import (
    AgentAction,
    AgentPhase,
    AgentStatus,
    ErrorEvent,
    Finished,
    TextDelta,
    ToolFinished,
    ToolStarted,
    UsageUpdated,
)
from ..agents import SmartRunner
from ..core.stats import UsageStats
from ..providers.store import ProviderStore
from ..rules.loader import load_rules
from ..rules.skills import discover_skills
from ..sessions import SessionStore


HTML = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Paicode Console</title>
<style>
:root { color-scheme: light; }
* { box-sizing: border-box; }
body { margin: 0; background: #fafafa; color: #111; font: 15px/1.5 ui-sans-serif, system-ui, sans-serif; }
header { display: flex; align-items: center; justify-content: space-between; padding: 16px 24px; border-bottom: 1px solid rgba(0,0,0,.08); background: #fff; }
h1 { font-size: 18px; margin: 0; letter-spacing: -.01em; }
main { display: grid; grid-template-columns: 320px 1fr; height: calc(100vh - 58px); }
aside { border-right: 1px solid rgba(0,0,0,.08); background: #fff; overflow: auto; }
section { padding: 20px 24px; overflow: auto; }
button { border: 1px solid rgba(0,0,0,.12); background: #111; color: #fff; border-radius: 10px; padding: 8px 14px; cursor: pointer; }
button.ghost { background: #fff; color: #111; }
button:hover { background: #262626; }
input, textarea { width: 100%; border: 1px solid rgba(0,0,0,.12); border-radius: 10px; padding: 10px 12px; font: inherit; background: #fff; }
textarea { min-height: 92px; resize: vertical; }
.session { padding: 12px 16px; border-bottom: 1px solid rgba(0,0,0,.06); cursor: pointer; }
.session:hover { background: #f4f4f5; }
.session strong { display: block; font-size: 13px; }
.session span { color: #71717a; font-size: 12px; }
.card { background: #fff; border: 1px solid rgba(0,0,0,.08); border-radius: 14px; padding: 18px; margin-bottom: 16px; }
.log { background: #0b0b0c; color: #d4d4d4; border-radius: 14px; padding: 16px; min-height: 280px; white-space: pre-wrap; font: 13px/1.55 ui-monospace, monospace; }
.row { display: flex; gap: 8px; align-items: center; }
.muted { color: #71717a; font-size: 12px; }
</style>
</head>
<body>
<header>
  <h1>Paicode Console</h1>
  <div class="row"><input id="token" placeholder="Server token" style="width:220px"><button class="ghost" onclick="saveToken()">Use token</button></div>
</header>
<main>
  <aside><div id="sessions"></div></aside>
  <section>
    <div class="card">
      <div class="row" style="justify-content:space-between"><strong id="session-title">Select a session</strong><span class="muted" id="session-meta"></span></div>
      <p class="muted">Run prompts through the same smart routing engine used by the terminal interface.</p>
      <textarea id="prompt" placeholder="Describe the task"></textarea>
      <div class="row" style="margin-top:10px"><button onclick="sendPrompt()">Run prompt</button><span class="muted" id="status"></span></div>
    </div>
    <div class="log" id="log">No run yet.</div>
  </section>
</main>
<script>
let active = null;
function token() { return localStorage.getItem('paicode-token') || ''; }
function saveToken() { localStorage.setItem('paicode-token', document.getElementById('token').value.trim()); loadSessions(); }
async function api(path, options = {}) {
  const headers = Object.assign({'Authorization': 'Bearer ' + token()}, options.headers || {});
  const response = await fetch(path, Object.assign({}, options, {headers}));
  if (!response.ok) throw new Error(await response.text());
  return response.json();
}
async function loadSessions() {
  const box = document.getElementById('sessions');
  try {
    const rows = await api('/api/sessions');
    box.innerHTML = rows.map(row => `<div class="session" onclick="openSession('${row.id}')"><strong>${row.title || row.id}</strong><span>${row.workspace}</span><br><span>${row.last_opened_at}</span></div>`).join('') || '<p class="muted" style="padding:16px">No sessions.</p>';
  } catch (error) { box.innerHTML = '<p class="muted" style="padding:16px">Set a valid token.</p>'; }
}
async function openSession(id) {
  active = await api('/api/sessions/' + id);
  document.getElementById('session-title').textContent = active.title || active.id;
  document.getElementById('session-meta').textContent = active.workspace;
  document.getElementById('log').textContent = (active.transcript || []).map(item => (item.kind || '') + ': ' + (item.text || item.name || item.detail || '')).join('\\n') || 'No transcript yet.';
}
async function sendPrompt() {
  if (!active) return;
  const prompt = document.getElementById('prompt').value.trim();
  if (!prompt) return;
  document.getElementById('status').textContent = 'running';
  const result = await api('/api/sessions/' + active.id + '/prompt', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({prompt})});
  const source = new EventSource('/api/runs/' + result.run_id + '/events?token=' + encodeURIComponent(token()));
  const log = document.getElementById('log');
  log.textContent = '';
  source.onmessage = event => {
    const data = JSON.parse(event.data);
    if (data.type === 'TextDelta') log.textContent += data.text;
    else if (data.type === 'ToolStarted') log.textContent += '\\n[' + data.name + '] ';
    else if (data.type === 'Finished') { document.getElementById('status').textContent = 'done'; source.close(); }
    else if (data.type === 'ErrorEvent') { log.textContent += '\\nerror: ' + data.message; document.getElementById('status').textContent = 'failed'; source.close(); }
  };
}
document.getElementById('token').value = token();
loadSessions();
</script>
</body>
</html>
"""


@dataclass
class RunState:
    id: str
    session_id: str
    status: str = "running"
    events: list[dict] = field(default_factory=list)
    done: threading.Event = field(default_factory=threading.Event)
    error: str = ""


RUNS: dict[str, RunState] = {}
RUNS_LOCK = threading.Lock()


def event_to_dict(event) -> dict | None:
    if isinstance(event, UsageUpdated):
        stats = event.stats
        return {
            "type": "UsageUpdated",
            "total_tokens": getattr(stats, "total_tokens", 0),
            "cost_usd": round(getattr(stats, "cost_usd", 0.0), 6),
        }
    if isinstance(event, (TextDelta, ToolStarted, ToolFinished, Finished, ErrorEvent, AgentPhase, AgentStatus, AgentAction)):
        payload = asdict(event)
        payload["type"] = type(event).__name__
        return payload
    return None


def _append_run_event(run: RunState, event) -> None:
    payload = event_to_dict(event)
    if payload is not None:
        run.events.append(payload)


class ApiHandler(BaseHTTPRequestHandler):
    server_version = f"Paicode/{__version__}"

    def log_message(self, format: str, *args) -> None:
        return

    @property
    def token(self) -> str:
        return getattr(self.server, "token", "")

    def _authorized(self, query: dict | None = None) -> bool:
        if not self.token:
            return True
        header = self.headers.get("Authorization", "")
        if header == f"Bearer {self.token}":
            return True
        if query and query.get("token", [""])[0] == self.token:
            return True
        return False

    def _send(self, status: int, payload: dict | list, content_type: str = "application/json") -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8") if not isinstance(payload, bytes) else payload
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0") or 0)
        if length <= 0:
            return {}
        try:
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return {}
        return payload if isinstance(payload, dict) else {}

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query)
        if parsed.path == "/" and self._authorized(query):
            self._send(200, HTML.encode("utf-8"), "text/html; charset=utf-8")
            return
        if not self._authorized(query):
            self._send(401, {"error": "unauthorized"})
            return
        if parsed.path == "/health":
            self._send(200, {"status": "ok", "version": __version__})
            return
        if parsed.path == "/api/sessions":
            self._send(200, [record.to_dict() for record in SessionStore().list()])
            return
        if parsed.path.startswith("/api/sessions/"):
            session_id = parsed.path.rsplit("/", 1)[-1]
            data = SessionStore().get(session_id)
            if data is None:
                self._send(404, {"error": "session not found"})
                return
            self._send(200, data.to_dict())
            return
        if parsed.path.startswith("/api/runs/"):
            run_id = parsed.path.split("/")[3]
            self._stream_run(run_id, query)
            return
        self._send(404, {"error": "not found"})

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if not self._authorized():
            self._send(401, {"error": "unauthorized"})
            return
        if parsed.path == "/api/sessions":
            payload = self._read_json()
            workspace = str(payload.get("workspace", "")).strip()
            if not workspace:
                self._send(400, {"error": "workspace is required"})
                return
            root = Path(workspace).expanduser().resolve()
            if not root.is_dir():
                self._send(400, {"error": "workspace does not exist"})
                return
            data = SessionStore().create(root, str(payload.get("title", "")).strip())
            self._send(201, data.record.to_dict())
            return
        if parsed.path.startswith("/api/sessions/") and parsed.path.endswith("/prompt"):
            session_id = parsed.path.split("/")[3]
            payload = self._read_json()
            prompt = str(payload.get("prompt", "")).strip()
            if not prompt:
                self._send(400, {"error": "prompt is required"})
                return
            data = SessionStore().get(session_id)
            if data is None:
                self._send(404, {"error": "session not found"})
                return
            run = RunState(id=f"run-{uuid4().hex[:10]}", session_id=session_id)
            with RUNS_LOCK:
                RUNS[run.id] = run
            threading.Thread(target=self._execute, args=(run, data, prompt), daemon=True).start()
            self._send(202, {"run_id": run.id, "session_id": session_id})
            return
        self._send(404, {"error": "not found"})

    def _execute(self, run: RunState, data, prompt: str) -> None:
        store = ProviderStore()
        provider = store.active()
        try:
            if provider is None or not provider.api_keys:
                raise RuntimeError("No provider configured.")
            root = Path(data.record.workspace).expanduser().resolve()
            stats = UsageStats.from_dict(data.stats) if data.stats else UsageStats()
            runner = SmartRunner(
                root,
                provider,
                stats,
                load_rules(root),
                discover_skills(root),
                emit=lambda event: _append_run_event(run, event),
                session_id=data.record.id,
            )
            data.transcript.append({"kind": "user", "text": prompt})
            text = runner.run(prompt)
            data.transcript.append({"kind": "assistant", "text": text})
            data.stats = stats.to_dict()
            SessionStore().save(data)
        except Exception as exc:
            run.error = f"{type(exc).__name__}: {exc}"
            run.events.append({"type": "ErrorEvent", "message": run.error})
        finally:
            run.status = "failed" if run.error else "done"
            run.done.set()

    def _stream_run(self, run_id: str, query: dict) -> None:
        with RUNS_LOCK:
            run = RUNS.get(run_id)
        if run is None:
            self._send(404, {"error": "run not found"})
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "close")
        self.end_headers()
        index = 0
        while True:
            while index < len(run.events):
                payload = json.dumps(run.events[index], ensure_ascii=False)
                self.wfile.write(f"data: {payload}\n\n".encode("utf-8"))
                self.wfile.flush()
                index += 1
            if run.done.is_set() and index >= len(run.events):
                break
            if not run.done.wait(timeout=0.25):
                try:
                    self.wfile.write(b": heartbeat\n\n")
                    self.wfile.flush()
                except OSError:
                    return
        self.wfile.write(b"event: done\ndata: {}\n\n")
        self.wfile.flush()
        self.close_connection = True


def create_server(host: str = "127.0.0.1", port: int = 8765, token: str = "") -> ThreadingHTTPServer:
    server = ThreadingHTTPServer((host, int(port)), ApiHandler)
    server.daemon_threads = True
    server.token = token or secrets.token_urlsafe(24)
    return server
