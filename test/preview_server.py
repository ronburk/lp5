#!/usr/bin/env python3
"""Test-only allowlisted HTTP server for the LP5 cloud-browser fixture."""

from __future__ import annotations

import argparse
import json
import mimetypes
import os
import re
import signal
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path, PurePosixPath
from urllib.parse import unquote, urlsplit

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_ROOT = REPO_ROOT / "test-fixtures" / "lp5-test-project.lp5"


class PreviewHandler(BaseHTTPRequestHandler):
    def _storage_path(self):
        path = unquote(urlsplit(self.path).path)
        prefix = next((prefix for prefix in ("/test/storage-project/", "/test/storage-project.lp5/")
                       if path.startswith(prefix)), None)
        if prefix is None:
            return None
        name = path[len(prefix):]
        if not name:
            return self.server.storage_root
        if name in {".", ".."} or re.search(r'[\x00-\x1f\x7f/\\<>:"|?*]', name) or name.endswith((".", " ")):
            return None
        return self.server.storage_root / name

    def do_PUT(self):
        target = self._storage_path()
        if target is None or target == self.server.storage_root:
            self.send_error(404)
            return
        try:
            size = int(self.headers.get("Content-Length", "-1"))
            if not 0 <= size <= 1024 * 1024:
                self.send_error(413)
                return
            body = self.rfile.read(size)
            if len(body) != size:
                self.send_error(400)
                return
            with tempfile.NamedTemporaryFile(dir=target.parent.parent, delete=False) as staged:
                temporary = Path(staged.name)
                try:
                    staged.write(body)
                    staged.close()
                    temporary.replace(target)
                finally:
                    temporary.unlink(missing_ok=True)
            self.send_response(204)
            self.end_headers()
        except (ValueError, OSError) as error:
            self.send_error(400, str(error))

    def do_DELETE(self):
        target = self._storage_path()
        if target is None or target == self.server.storage_root or not target.is_file():
            self.send_error(404)
            return
        target.unlink()
        self.send_response(204)
        self.end_headers()

    def do_GET(self):
        self._serve(head_only=False)

    def do_HEAD(self):
        self._serve(head_only=True)

    def _serve(self, *, head_only: bool):
        target = self._storage_path()
        if target is not None:
            if target == self.server.storage_root:
                body = json.dumps(sorted(p.name for p in target.iterdir() if p.is_file())).encode()
                content_type = "application/json"
            elif target.is_file():
                body = target.read_bytes()
                content_type = "text/plain"
            else:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header("Content-Type", f"{content_type}; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            if not head_only:
                self.wfile.write(body)
            return
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
        elif path == "/test/output_fixture.json":
            generated = subprocess.run([sys.executable, str(REPO_ROOT / "test" / "output_fixture.py")],
                                       cwd=REPO_ROOT, capture_output=True, check=True)
            body = generated.stdout
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            if not head_only:
                self.wfile.write(body)
            return
        elif path == "/test/state_machine_compiler.js":
            compiled = subprocess.run(
                [str(REPO_ROOT / "lp5"), "lp5", "show-bundle", "State Machine Compiler"],
                cwd=REPO_ROOT, capture_output=True, check=True)
            body = ET.fromstring(compiled.stdout).find("section/code").text.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/javascript; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            if not head_only:
                self.wfile.write(body)
            return
        elif path == "/lp5.lp5/lp5.out":
            target = REPO_ROOT / "lp5.lp5" / "lp5.out"
        elif path in {"/test/browser_db.html", "/test/model_load_project.html", "/test/storage.html", "/test/startup_errors.html", "/test/select_project.html", "/test/state_machine_compiler.html", "/test/unit_startup.html", "/test/view_articles.html", "/test/view_toc.html", "/test/view_output.html"}:
            target = REPO_ROOT / "test" / relative.name
        elif path in {"/test/project_io_controls.js", "/test/move_article.js", "/test/output_selection.js", "/test/toc_expansion.js"}:
            target = REPO_ROOT / "test" / relative.name
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
        if path == "/lp5.lp5/lp5.out":
            content_type = "text/html"
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
    parser.add_argument(
        "--strictPort",
        action="store_true",
        help="accepted for sites-preview compatibility",
    )
    args = parser.parse_args()
    host = args.host or args.forwarded_host or os.environ.get("HOST", "0.0.0.0")
    port = args.port or args.forwarded_port or int(os.environ.get("PORT", "8000"))
    server = ThreadingHTTPServer((host, port), PreviewHandler)
    storage_directory = tempfile.TemporaryDirectory(prefix="lp5-storage-preview-")
    server.storage_root = Path(storage_directory.name)
    def stop(signum, frame):
        raise KeyboardInterrupt
    signal.signal(signal.SIGTERM, stop)
    print(f"LP5 test preview listening on {host}:{port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        storage_directory.cleanup()


if __name__ == "__main__":
    main()
