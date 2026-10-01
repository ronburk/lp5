#!/usr/bin/env python3
"""Check that commands refresh weave.xml only when source timestamps require it."""

import os
import subprocess
import sys
import tempfile
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parents[1]
STYLESHEETS = (
    "add-article.xsl",
    "check.xsl",
    "show-bundle.xsl",
    "tangle.xsl",
    "weave.xsl",
)


def run(executable, working_directory, source_directory, *arguments):
    return subprocess.run(
        [executable, "-s", str(source_directory), *arguments],
        cwd=working_directory,
        text=True,
        capture_output=True,
    )


def main():
    if len(sys.argv) != 2:
        raise SystemExit(f"usage: {sys.argv[0]} /path/to/lp5")
    executable = str(Path(sys.argv[1]).resolve())

    with tempfile.TemporaryDirectory(prefix="lp5-weave-freshness-") as temporary:
        directory = Path(temporary)
        working_directory = directory / "working"
        source_directory = directory / "source"
        working_directory.mkdir()
        source_directory.mkdir()
        for stylesheet in STYLESHEETS:
            (working_directory / stylesheet).symlink_to(PROJECT_DIR / stylesheet)

        (source_directory / "lp5.lp5").write_text(
            "<template><children><li id=\"1.lp5\"/></children></template>\n",
            encoding="utf-8",
        )
        article = source_directory / "1.lp5"
        article.write_text(
            "<template><heading>First version</heading></template>\n",
            encoding="utf-8",
        )

        weave_file = working_directory / "weave.xml"
        checked_file = working_directory / "checked.xml"
        checked = run(
            executable, working_directory, source_directory,
            "-o", str(checked_file), "check", "1",
        )
        assert checked.returncode == 0, checked.stderr
        assert "Valid article:" in checked_file.read_text(encoding="utf-8")
        assert "<lp5-weave" in weave_file.read_text(encoding="utf-8")

        fresh_mtime = weave_file.stat().st_mtime_ns
        checked = run(executable, working_directory, source_directory, "check", "1")
        assert checked.returncode == 0, checked.stderr
        assert weave_file.stat().st_mtime_ns == fresh_mtime

        newest_source_mtime = max(
            source_directory.stat().st_mtime_ns,
            (source_directory / "lp5.lp5").stat().st_mtime_ns,
            article.stat().st_mtime_ns,
        )
        os.utime(weave_file, ns=(newest_source_mtime, newest_source_mtime))
        checked = run(executable, working_directory, source_directory, "check", "1")
        assert checked.returncode == 0, checked.stderr
        assert weave_file.stat().st_mtime_ns > newest_source_mtime

        source_directory_mtime = source_directory.stat().st_mtime_ns
        os.utime(weave_file, ns=(0, 0))
        article.write_text(
            "<template><heading>Edited article</heading></template>\n",
            encoding="utf-8",
        )
        assert source_directory.stat().st_mtime_ns == source_directory_mtime
        checked = run(executable, working_directory, source_directory, "check", "1")
        assert checked.returncode == 0, checked.stderr
        assert "Edited article" in weave_file.read_text(encoding="utf-8")

        fresh_mtime = weave_file.stat().st_mtime_ns
        stale_mtime = fresh_mtime - 10_000_000_000
        for source_file in (source_directory / "lp5.lp5", article):
            os.utime(source_file, ns=(stale_mtime - 2_000_000_000,
                                      stale_mtime - 2_000_000_000))
        os.utime(weave_file, ns=(stale_mtime, stale_mtime))
        orphan = source_directory / "2.lp5"
        orphan.write_text(
            "<template><heading>New orphan</heading></template>\n",
            encoding="utf-8",
        )
        os.utime(orphan, ns=(stale_mtime - 1_000_000_000,
                             stale_mtime - 1_000_000_000))
        source_directory_time = stale_mtime + 2_000_000_000
        os.utime(source_directory, ns=(source_directory_time,
                                        source_directory_time))
        assert all((source_directory / filename).stat().st_mtime_ns < stale_mtime
                   for filename in ("lp5.lp5", "1.lp5", "2.lp5"))
        assert source_directory.stat().st_mtime_ns > stale_mtime
        checked = run(executable, working_directory, source_directory, "check", "1")
        assert checked.returncode == 0, checked.stderr
        assert "New orphan" in weave_file.read_text(encoding="utf-8")

        os.utime(weave_file, ns=(0, 0))
        checked = run(
            executable, working_directory, source_directory,
            "check.xsl", str(article),
        )
        assert checked.returncode == 0, checked.stderr
        assert "Valid article:" in checked.stdout
        assert weave_file.stat().st_mtime_ns > 0

        # The weave command itself must run without refreshing the canonical index.
        stale_mtime = weave_file.stat().st_mtime_ns
        os.utime(article, ns=(stale_mtime + 2_000_000_000,
                              stale_mtime + 2_000_000_000))
        explicit_weave = working_directory / "explicit-weave.xml"
        woven = run(
            executable, working_directory, source_directory,
            "-o", str(explicit_weave), "weave",
        )
        assert woven.returncode == 0, woven.stderr
        assert explicit_weave.exists()
        assert weave_file.stat().st_mtime_ns == stale_mtime

        stale_mtime = weave_file.stat().st_mtime_ns
        os.utime(article, ns=(stale_mtime + 4_000_000_000,
                              stale_mtime + 4_000_000_000))
        direct_weave = run(
            executable, working_directory, source_directory,
            "weave.xsl", str(source_directory / "lp5.lp5"),
        )
        assert direct_weave.returncode == 0, direct_weave.stderr
        assert "<lp5-weave" in direct_weave.stdout
        assert weave_file.stat().st_mtime_ns == stale_mtime

        # An unsuccessful preflight must stop the requested check command.
        os.utime(weave_file, ns=(0, 0))
        (source_directory / "lp5.lp5").write_text("<broken", encoding="utf-8")
        not_created = working_directory / "must-not-exist.xml"
        failed = run(
            executable, working_directory, source_directory,
            "-o", str(not_created), "check", "1",
        )
        assert failed.returncode != 0
        assert "requested command was not run" in failed.stderr
        assert not not_created.exists()

    print("weave freshness preflight test passed")


if __name__ == "__main__":
    main()
