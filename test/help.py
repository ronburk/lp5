#!/usr/bin/env python3
"""Check that both help forms print usage successfully."""

import subprocess
import sys
from pathlib import Path


def main():
    if len(sys.argv) != 2:
        raise SystemExit(f"usage: {sys.argv[0]} /path/to/lp5")

    executable = str(Path(sys.argv[1]).resolve())
    outputs = []
    for argument in ("--help", "help"):
        result = subprocess.run([executable, argument], capture_output=True)
        assert result.returncode == 0, result.stderr
        assert result.stdout == b"", result.stdout
        assert b"Usage:" in result.stderr, result.stderr
        assert b"unknown command" not in result.stderr, result.stderr
        outputs.append(result.stderr)
    assert outputs[0] == outputs[1], outputs
    print("help command checks passed")


if __name__ == "__main__":
    main()
