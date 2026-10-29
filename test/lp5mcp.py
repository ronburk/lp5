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
        project = Path(directory) / "demo.lp5"
        project.mkdir()
        messages = [
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
            {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {
                "name": "check", "arguments": {"article": "1.lp5"}}},
            {"jsonrpc": "2.0", "id": 4, "method": "tools/call", "params": {
                "name": "select_project", "arguments": {"path": "demo"}}},
            {"jsonrpc": "2.0", "id": 5, "method": "tools/call", "params": {
                "name": "check", "arguments": {"article": "1.lp5"}}},
            {"jsonrpc": "2.0", "id": 6, "method": "unknown", "params": {}},
        ]
        payload = "".join(json.dumps(message) + "\n" for message in messages)
        result = subprocess.run([str(server), directory], input=payload,
                                text=True, capture_output=True,
                                env={**os.environ, "LP5_SERVER_URL": "", "LP5_EXECUTABLE": str(fake)})
        assert result.returncode == 0, result.stderr
        replies = [json.loads(line) for line in result.stdout.splitlines()]
        assert [reply["id"] for reply in replies] == [1, 2, 3, 4, 5, 6]
        assert replies[0]["result"]["capabilities"] == {"tools": {}}
        assert {tool["name"] for tool in replies[1]["result"]["tools"]} == {
            "select_project", "check", "show_article", "show_bundle", "weave", "tangle"}
        assert replies[2]["error"]["code"] == -32000
        assert replies[3]["result"]["content"][0]["text"] == "project selected"
        assert replies[4]["result"]["content"][0]["text"] == "fake-output:demo check 1.lp5\n"
        assert replies[5]["error"]["code"] == -32601
        assert not result.stderr
        env = {**os.environ, "LP5_SERVER_URL": "", "LP5_EXECUTABLE": str(fake)}

        def invoke(args, requests=messages[:3], remote=False):
            return subprocess.run([str(server), *args],
                input="".join(json.dumps(m) + "\n" for m in requests),
                cwd=directory, text=True, capture_output=True,
                env={**env, "LP5_SERVER_URL": "https://example.invalid/lp5" if remote else ""})

        for args in [[], [""], ["one", "two"], [str(fake)],
                     ["https://example.invalid/project"], ["--unknown"]]:
            result = invoke(args)
            assert result.returncode == 2 and result.stderr and not result.stdout, result
        for flag in ["--help", "-h", "-?"]:
            result = invoke([flag])
            assert result.returncode == 0 and "LOCAL_PROJECT_DIRECTORY" in result.stdout
            assert "LP5_SERVER_URL" in result.stdout and not result.stderr
        for path in ["demo.lp5", str(project), "demo.lp5/", "./demo.lp5/."]:
            result = invoke([path])
            assert result.returncode == 0 and not result.stderr, result
            replies = [json.loads(line) for line in result.stdout.splitlines()]
            assert replies[2]["result"]["content"][0]["text"] == "fake-output:demo check 1.lp5\n"
        for path in ["future/nested", "future/new.lp5", "-checkout"]:
            for remote in [False, True]:
                result = invoke(["--", path], messages[:2], remote=remote)
                assert result.returncode == 0 and not result.stderr, result
                assert not (Path(directory) / path).exists()
        result = invoke(["demo.lp5"], remote=True)
        replies = [json.loads(line) for line in result.stdout.splitlines()]
        assert replies[2]["error"]["code"] == -32000
        assert {t["name"] for t in replies[1]["result"]["tools"]} == {"select_project", "check"}
        result = invoke(["checkout"], messages[:2] + [messages[3]], remote=True)
        replies = [json.loads(line) for line in result.stdout.splitlines()]
        assert replies[2]["result"]["content"][0]["text"] == "project selected"
        assert not result.stderr
    print("lp5mcp: PASS")


if __name__ == "__main__":
    main()
