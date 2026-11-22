import json
import urllib.error
import urllib.request
from urllib.parse import quote


class PaicodeClient:
    def __init__(self, base_url: str = "http://127.0.0.1:8765", token: str = "", timeout: int = 30):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.timeout = max(1, int(timeout))

    def _request(self, method: str, path: str, payload: dict | None = None) -> dict | list:
        data = None
        headers = {"Accept": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(self.base_url + path, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"HTTP {exc.code}: {detail}") from exc

    def health(self) -> dict:
        return self._request("GET", "/health")

    def sessions(self) -> list[dict]:
        return self._request("GET", "/api/sessions")

    def create_session(self, workspace: str, title: str = "") -> dict:
        return self._request("POST", "/api/sessions", {"workspace": workspace, "title": title})

    def session(self, session_id: str) -> dict:
        return self._request("GET", f"/api/sessions/{quote(session_id)}")

    def prompt(self, session_id: str, prompt: str) -> dict:
        return self._request("POST", f"/api/sessions/{quote(session_id)}/prompt", {"prompt": prompt})

    def events_url(self, run_id: str) -> str:
        suffix = f"?token={quote(self.token)}" if self.token else ""
        return f"{self.base_url}/api/runs/{quote(run_id)}/events{suffix}"
