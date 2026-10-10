#!/usr/bin/env python3
"""Check source-local indexes, project switching, and relative add paths."""

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
        projects = [working / "first project", working / "second project"]
        for source in projects:
            source.mkdir()
            (source / "lp5.lp5").write_text(
                f"<template><heading>{source.name}</heading></template>",
                encoding="utf-8",
            )

        def run(*args, environment=None):
            result = subprocess.run([executable, *args], cwd=working,
                                    env=environment, capture_output=True)
            assert result.returncode == 0, result.stderr
            assert not result.stderr, result.stderr
            return result

        # An obsolete working-directory index must never substitute for a
        # project's own index, even when it has a future timestamp.
        old_index = working / "weave.xml"
        old_index.write_bytes(b"obsolete index")
        future = old_index.stat().st_mtime_ns + 10_000_000_000
        os.utime(old_index, ns=(future, future))

        first, second = projects
        run("-s", first.name, "show-bundle")
        first_cache = first / "weave.xml"
        first_time = first_cache.stat().st_mtime_ns
        assert ET.parse(first_cache).findtext("articles/article/heading") == first.name
        run("-s", first.name + "/", "show-bundle")
        assert first_cache.stat().st_mtime_ns == first_time

        # Environment selection and command-line override each use the chosen
        # source's cache without replacing or rebuilding another project's.
        environment = dict(os.environ, LP5Source=second.name)
        run("show-bundle", environment=environment)
        second_cache = second / "weave.xml"
        second_time = second_cache.stat().st_mtime_ns
        assert ET.parse(second_cache).findtext("articles/article/heading") == second.name
        run("-s", first.name, "show-bundle", environment=environment)
        assert first_cache.stat().st_mtime_ns == first_time
        assert second_cache.stat().st_mtime_ns == second_time
        assert old_index.read_bytes() == b"obsolete index"

        incoming = working / "incoming.lp5"
        incoming.write_bytes(b"<template><heading>Added</heading></template>")
        alternate_directory = working / "indexes"
        alternate_directory.mkdir()
        alternate = alternate_directory / "alternate.xml"
        # Relative source paths must work whether the index is in the source
        # directory or in a different directory (the earlier /tmp failure).
        for options in ([], ["-w", str(alternate)]):
            result = subprocess.run(
                [executable, "-s", first.name, *options, "add-article",
                 "lp5.lp5", incoming.name], cwd=working, capture_output=True,
            )
            assert result.returncode == 0, result.stderr
            assert result.stderr.startswith(b"added article: "), result.stderr
            assert b"warning" not in result.stderr.lower(), result.stderr
        children = ET.parse(first / "lp5.lp5").findall("children/li")
        assert len(children) == 2
        for child in children:
            assert (first / child.get("id")).read_bytes() == incoming.read_bytes()

        # Deleting the disposable index causes automatic reconstruction.
        first_cache.unlink()
        run("-s", first.name, "show-bundle")
        assert len(ET.parse(first_cache).findall("articles/article")) == 3
        fresh_time = first_cache.stat().st_mtime_ns
        run("-s", first.name, "show-bundle")
        assert first_cache.stat().st_mtime_ns == fresh_time

    print("source-local index and relative article path checks passed")


if __name__ == "__main__":
    main()
