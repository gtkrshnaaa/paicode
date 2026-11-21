import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from paicode.core.errors import ProviderError
from paicode.providers.client import ProviderClient
from paicode.providers.store import ProviderConfig


class SlowHandler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        return

    def do_POST(self):
        self.rfile.read(int(self.headers.get("Content-Length", "0")))
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.end_headers()
        chunk = {
            "id": "slow",
            "object": "chat.completion.chunk",
            "created": 0,
            "model": "fake",
            "choices": [{"index": 0, "delta": {"content": "partial"}, "finish_reason": None}],
        }
        self.wfile.write(f"data: {json.dumps(chunk)}\n\n".encode())
        self.wfile.flush()
        time.sleep(5)
        self.wfile.write(b"data: [DONE]\n\n")
        self.wfile.flush()


def test_provider_stream_aborts_immediately_on_stop():
    server = ThreadingHTTPServer(("127.0.0.1", 0), SlowHandler)
    server.daemon_threads = True
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address
    provider = ProviderConfig(
        name="fake",
        base_url=f"http://{host}:{port}/v1",
        api_keys=["test-key"],
        model="fake-model",
    )
    stop = threading.Event()
    threading.Timer(0.3, stop.set).start()
    started = time.monotonic()
    try:
        with pytest.raises(ProviderError, match="Stopped by user"):
            ProviderClient(provider).stream(
                [{"role": "user", "content": "talk"}],
                None,
                stop_event=stop,
            )
        elapsed = time.monotonic() - started
        assert elapsed < 3
    finally:
        server.shutdown()
        server.server_close()
