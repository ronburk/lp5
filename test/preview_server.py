#!/usr/bin/env python3
"""Test-only allowlisted HTTP server for the LP5 cloud-browser fixture."""

from __future__ import annotations

import argparse
import mimetypes
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path, PurePosixPath
from urllib.parse import unquote, urlsplit

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_ROOT = REPO_ROOT / "test-fixtures" / "lp5-test-project.lp5"


class PreviewHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self._serve(head_only=False)

    def do_HEAD(self):
        self._serve(head_only=True)

    def _serve(self, *, head_only: bool):
        path = unquote(urlsplit(self.path).path)
        if "\\" in path or "\x00" in path:
            self.send_error(404)
            return

        relative = PurePosixPath(path.lstrip("/"))
        if any(part in (".", "..") for part in relative.parts):
            self.send_error(404)
            return

        if path == "/new.html":
            target = REPO_ROOT / "new.html"
        elif path == "/test/project_io_controls.js":
            target = REPO_ROOT / "test" / "project_io_controls.js"
        elif relative.parts[:1] == ("test-fixtures",):
            if len(relative.parts) != 3 or relative.parts[1] != "lp5-test-project.lp5":
                self.send_error(404)
                return
            filename = relative.parts[2]
            if filename not in {"lp5-test-project.lp5", "0.lp5", "1.lp5"}:
                self.send_error(404)
                return
            target = FIXTURE_ROOT / filename
        else:
            self.send_error(404)
            return

        resolved = target.resolve()
        if not resolved.is_relative_to(REPO_ROOT) or not resolved.is_file():
            self.send_error(404)
            return

        body = resolved.read_bytes()
        content_type = mimetypes.guess_type(resolved.name)[0] or "application/octet-stream"
        self.send_response(200)
        self.send_header("Content-Type", f"{content_type}; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        if not head_only:
            self.wfile.write(body)

    def log_message(self, fmt, *args):
        print(f"{self.address_string()} - {fmt % args}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("forwarded_host", nargs="?", help="optional preview host")
    parser.add_argument("forwarded_port", nargs="?", type=int, help="optional preview port")
    parser.add_argument("--host", default=None, help="bind address (or HOST environment variable)")
    parser.add_argument("--port", type=int, default=None, help="bind port (or PORT environment variable)")
    args = parser.parse_args()
    host = args.host or args.forwarded_host or os.environ.get("HOST", "0.0.0.0")
    port = args.port or args.forwarded_port or int(os.environ.get("PORT", "8000"))
    server = ThreadingHTTPServer((host, port), PreviewHandler)
    print(f"LP5 test preview listening on {host}:{port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
