#!/usr/bin/env python3
"""Check project-name selection, fixed local indexes, and relative add paths."""

import os
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parents[1]


def main():
    executable = str(Path(sys.argv[1]).resolve())
    with tempfile.TemporaryDirectory(prefix="lp5-source-index-") as temporary:
        working = Path(temporary)
        for stylesheet in ("weave.xsl", "tangle.xsl", "show-bundle.xsl",
                           "add-article.xsl", "check.xsl"):
            (working / stylesheet).symlink_to(PROJECT_DIR / stylesheet)
        projects = {
            "first project": working / "first project.lp5",
            "second project": working / "second project.lp5",
        }
        for name, source in projects.items():
            source.mkdir()
            (source / f"{name}.lp5").write_text(
                f"<template><heading>{name}</heading></template>",
                encoding="utf-8",
            )

        def run(project, *arguments):
            result = subprocess.run([executable, project, *arguments], cwd=working,
                                    capture_output=True)
            assert result.returncode == 0, result.stderr.decode("utf-8")
            assert not result.stderr, result.stderr
            return result

        # A stale working-directory index cannot substitute for a project cache.
        old_index = working / "weave.xml"
        old_index.write_bytes(b"obsolete index")
        future = old_index.stat().st_mtime_ns + 10_000_000_000
        os.utime(old_index, ns=(future, future))

        first, second = projects
        run(first, "show-bundle")
        first_cache = projects[first] / "weave.xml"
        first_time = first_cache.stat().st_mtime_ns
        assert ET.parse(first_cache).findtext("articles/article/heading") == first
        run(second, "show-bundle")
        second_cache = projects[second] / "weave.xml"
        assert ET.parse(second_cache).findtext("articles/article/heading") == second
        assert old_index.read_bytes() == b"obsolete index"

        incoming = working / "incoming.lp5"
        incoming.write_bytes(b"<template><heading>Added</heading></template>")
        result = subprocess.run(
            [executable, first, "add-article", f"{first}.lp5", incoming.name],
            cwd=working, capture_output=True,
        )
        assert result.returncode == 0, result.stderr
        assert result.stderr.startswith(b"added article: "), result.stderr
        children = ET.parse(projects[first] / f"{first}.lp5").findall("children/li")
        assert len(children) == 1
        assert (projects[first] / children[0].get("id")).read_bytes() == incoming.read_bytes()

        (projects[first] / "weave.xml").unlink()
        run(first, "show-bundle")
        assert len(ET.parse(first_cache).findall("articles/article")) == 2
        assert first_cache.stat().st_mtime_ns != first_time
        run(second, "show-bundle")
        assert len(ET.parse(second_cache).findall("articles/article")) == 1

        rejected = subprocess.run([executable, "-s", first, "show-bundle"],
                                  cwd=working, capture_output=True)
        assert rejected.returncode == 1
        assert old_index.read_bytes() == b"obsolete index"

    print("project-local index and article path checks passed")


if __name__ == "__main__":
    main()
