#!/usr/bin/env python3
"""Check the project-local weave cache freshness contract."""

import os
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parents[1]


def run(executable, working, *arguments):
    return subprocess.run([executable, "project", *arguments], cwd=working,
                          text=True, capture_output=True)


def main():
    if len(sys.argv) != 2:
        raise SystemExit(f"usage: {sys.argv[0]} /path/to/lp5")
    executable = str(Path(sys.argv[1]).resolve())

    with tempfile.TemporaryDirectory(prefix="lp5-weave-freshness-") as temporary:
        working = Path(temporary)
        source = working / "project.lp5"
        source.mkdir()
        for stylesheet in ("weave.xsl", "tangle.xsl", "check.xsl"):
            (working / stylesheet).symlink_to(PROJECT_DIR / stylesheet)
        root = source / "project.lp5"
        root.write_text(
            '<template><children><li id="1.lp5"/></children></template>\n',
            encoding="utf-8",
        )
        article = source / "1.lp5"
        article.write_text(
            "<template><heading>First version</heading></template>\n",
            encoding="utf-8",
        )
        cache = source / "weave.xml"

        woven = run(executable, working, "weave")
        assert woven.returncode == 0 and not woven.stdout, woven.stderr
        assert "<lp5-weave" in cache.read_text(encoding="utf-8")

        checked = run(executable, working, "check", "1")
        assert checked.returncode == 0 and "Valid article:" in checked.stdout
        fresh_time = cache.stat().st_mtime_ns
        assert run(executable, working, "check", "1").returncode == 0
        assert cache.stat().st_mtime_ns == fresh_time

        article.write_text(
            "<template><heading>Edited article</heading></template>\n",
            encoding="utf-8",
        )
        os.utime(cache, ns=(0, 0))
        checked = run(executable, working, "check", "1")
        assert checked.returncode == 0, checked.stderr
        assert "Edited article" in cache.read_text(encoding="utf-8")

        # Directory timestamps detect newly added files as well as edits.
        os.utime(cache, ns=(0, 0))
        (source / "2.lp5").write_text(
            "<template><heading>New orphan</heading></template>\n",
            encoding="utf-8",
        )
        checked = run(executable, working, "check", "1")
        assert checked.returncode == 0, checked.stderr
        assert "New orphan" in cache.read_text(encoding="utf-8")
        assert ET.parse(cache).find("articles/article[@file='2.lp5']") is not None

        # Project files are fixed by the project name; old override syntax is rejected.
        alternate = working / "alternate.xml"
        rejected = run(executable, working, "-w", str(alternate), "weave")
        assert rejected.returncode == 1 and "unknown command" in rejected.stderr
        assert not alternate.exists()
        rejected = run(executable, working, "weave", "other-root.lp5")
        assert rejected.returncode == 1 and "Usage:" in rejected.stderr

        # A broken root prevents freshness regeneration and the requested command.
        root.write_text("<broken", encoding="utf-8")
        os.utime(cache, ns=(0, 0))
        failed = run(executable, working, "check", "1")
        assert failed.returncode != 0
        assert "requested command was not run" in failed.stderr

    print("weave freshness checks passed")


if __name__ == "__main__":
    main()
