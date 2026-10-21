"""A small local server that misbehaves on purpose, so we can watch retries happen.

/flaky/<n>   fails with 503 twice, then works
/limited     answers 429 with Retry-After: 1 once, then works
/slow        takes 30 seconds (longer than our timeout)
/missing     404, which we must NOT retry
/private/... disallowed in robots.txt
"""

import sys
import time
from collections import Counter
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

hits: Counter[str] = Counter()
PAGE = "<html><head><title>{0}</title></head><body><main><p>{0} worked.</p></main></body></html>"


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        hits[self.path] += 1
        if self.path == "/robots.txt":
            return self.reply(200, "User-agent: *\nDisallow: /private/\n", "text/plain")
        if self.path.startswith("/flaky/") and hits[self.path] <= 2:
            return self.reply(503, "try again later")
        if self.path == "/limited" and hits[self.path] == 1:
            return self.reply(429, "slow down", headers={"Retry-After": "1"})
        if self.path == "/slow":
            time.sleep(30)
        if self.path == "/missing":
            return self.reply(404, "not here")
        self.reply(200, PAGE.format(self.path))

    def reply(
        self, code: int, body: str, ctype: str = "text/html", headers: dict[str, str] | None = None
    ) -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        for key, value in (headers or {}).items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(body.encode())

    def log_message(self, format: str, *args: object) -> None:
        now = time.strftime("%H:%M:%S") + f".{int(time.time() * 1000) % 1000:03d}"
        print(f"{now}  {self.command} {self.path} -> {args[1]}", flush=True)


port = int(sys.argv[1]) if len(sys.argv) > 1 else 0
server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
print(f"flaky server on http://127.0.0.1:{server.server_port}", flush=True)
server.serve_forever()
