import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


def _chunk(delta=None, finish=None, usage=None):
    payload = {
        "id": "chatcmpl-test",
        "object": "chat.completion.chunk",
        "created": 0,
        "model": "fake-model",
        "choices": [],
    }
    if usage is not None:
        payload["usage"] = usage
    else:
        payload["choices"] = [{"index": 0, "delta": delta or {}, "finish_reason": finish}]
    return payload


def tool_chunk(call_id: str, name: str, arguments: str):
    return _chunk(
        {
            "tool_calls": [
                {
                    "index": 0,
                    "id": call_id,
                    "type": "function",
                    "function": {"name": name, "arguments": arguments},
                }
            ]
        }
    )


def text_chunk(text: str):
    return _chunk({"role": "assistant", "content": text})


def finish_chunk(reason: str = "stop"):
    return _chunk({}, finish=reason)


def usage_chunk(
    prompt: int = 10,
    completion: int = 5,
    total: int = 15,
    cache_hit: int = 0,
    cache_miss: int = 0,
):
    usage = {"prompt_tokens": prompt, "completion_tokens": completion, "total_tokens": total}
    if cache_hit or cache_miss:
        usage["prompt_cache_hit_tokens"] = cache_hit
        usage["prompt_cache_miss_tokens"] = cache_miss
    return _chunk(usage=usage)


class FakeOpenAI:
    def __init__(self, responder, model_ids: list[str] | None = None):
        self.responder = responder
        self.model_ids = model_ids or ["fake-model"]
        self.requests: list[dict] = []
        self._server = ThreadingHTTPServer(("127.0.0.1", 0), self._handler())
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)

    @property
    def base_url(self) -> str:
        host, port = self._server.server_address
        return f"http://{host}:{port}/v1"

    def __enter__(self):
        self._thread.start()
        return self

    def __exit__(self, *exc):
        self._server.shutdown()
        self._server.server_close()
        self._thread.join(timeout=5)

    def _handler(self):
        outer = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def log_message(self, format, *args):
                return

            def do_GET(self):
                body = json.dumps(
                    {
                        "object": "list",
                        "data": [
                            {"id": model_id, "object": "model", "created": 0, "owned_by": "test"}
                            for model_id in outer.model_ids
                        ],
                    }
                ).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Connection", "close")
                self.end_headers()
                self.wfile.write(body)
                self.close_connection = True

            def do_POST(self):
                length = int(self.headers.get("Content-Length", "0"))
                payload = json.loads(self.rfile.read(length) or b"{}")
                index = len(outer.requests)
                outer.requests.append(payload)
                chunks = outer.responder(index, payload)
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.send_header("Cache-Control", "no-cache")
                self.send_header("Connection", "close")
                self.end_headers()
                for chunk in chunks:
                    self.wfile.write(f"data: {json.dumps(chunk)}\n\n".encode())
                    self.wfile.flush()
                self.wfile.write(b"data: [DONE]\n\n")
                self.wfile.flush()
                self.close_connection = True

        return Handler
