from pathlib import Path

from .helpers import make_registry, run_command, write_file


def test_http_api_and_static_site_task(project: Path, stats):
    registry = make_registry(project, stats)
    write_file(
        registry,
        "index.html",
        "<!doctype html><html><body><h1>Matrix</h1></body></html>",
    )
    write_file(
        registry,
        "app.py",
        "import json\n"
        "from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer\n\n"
        "class Handler(BaseHTTPRequestHandler):\n"
        "    def do_GET(self):\n"
        "        if self.path == '/api/health':\n"
        "            body = json.dumps({'status': 'ok'}).encode()\n"
        "            self.send_response(200)\n"
        "            self.send_header('Content-Type', 'application/json')\n"
        "        elif self.path == '/':\n"
        "            body = open('index.html', 'rb').read()\n"
        "            self.send_response(200)\n"
        "            self.send_header('Content-Type', 'text/html')\n"
        "        else:\n"
        "            body = b'not found'\n"
        "            self.send_response(404)\n"
        "            self.send_header('Content-Type', 'text/plain')\n"
        "        self.send_header('Content-Length', str(len(body)))\n"
        "        self.end_headers()\n"
        "        self.wfile.write(body)\n\n"
        "    def log_message(self, *args):\n"
        "        pass\n\n"
        "def serve():\n"
        "    return ThreadingHTTPServer(('127.0.0.1', 0), Handler)\n",
    )
    write_file(
        registry,
        "test_api.py",
        "import json\n"
        "import threading\n"
        "import urllib.request\n"
        "from app import serve\n\n"
        "server = serve()\n"
        "threading.Thread(target=server.serve_forever, daemon=True).start()\n"
        "host, port = server.server_address\n"
        "base = f'http://{host}:{port}'\n"
        "with urllib.request.urlopen(base + '/api/health') as response:\n"
        "    payload = json.load(response)\n"
        "assert payload == {'status': 'ok'}\n"
        "with urllib.request.urlopen(base + '/') as response:\n"
        "    assert b'Matrix' in response.read()\n"
        "server.shutdown()\n"
        "print('web-ok')\n",
    )
    output = run_command(registry, "python3 test_api.py")
    assert "web-ok" in output
