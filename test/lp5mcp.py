#!/usr/bin/env python3
"""Exercise the lp5mcp stdio framing and basic MCP methods."""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


def main():
    server = Path(sys.argv[1]).resolve()
    with tempfile.TemporaryDirectory() as directory:
        fake = Path(directory) / "lp5"
        fake.write_text("#!/bin/sh\necho fake-output:$@\n", encoding="utf-8")
        fake.chmod(0o755)
        messages = [
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
            {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {
                "name": "check", "arguments": {"article": "1.lp5"}}},
            {"jsonrpc": "2.0", "id": 4, "method": "unknown", "params": {}},
        ]
        payload = "".join(json.dumps(message) + "\n" for message in messages)
        result = subprocess.run([str(server), "demo"], input=payload,
                                text=True, capture_output=True,
                                env={**os.environ, "LP5_EXECUTABLE": str(fake)})
        assert result.returncode == 0, result.stderr
        replies = [json.loads(line) for line in result.stdout.splitlines()]
        assert [reply["id"] for reply in replies] == [1, 2, 3, 4]
        assert replies[0]["result"]["capabilities"] == {"tools": {}}
        assert {tool["name"] for tool in replies[1]["result"]["tools"]} == {
            "check", "show_article", "show_bundle", "weave", "tangle"}
        assert replies[2]["result"]["content"][0]["text"] == "fake-output:demo check 1.lp5\n"
        assert replies[3]["error"]["code"] == -32601
        assert not result.stderr
    print("lp5mcp: PASS")


if __name__ == "__main__":
    main()
