#!/usr/bin/env python3
"""Check that commands refresh weave.xml only when source timestamps require it."""

import os
import subprocess
import sys
import tempfile
from pathlib import Path
import xml.etree.ElementTree as ET


PROJECT_DIR = Path(__file__).resolve().parents[1]
STYLESHEETS = (
    "add-article.xsl",
    "check.xsl",
    "list-keywords.xsl",
    "search-keywords.xsl",
    "search.xsl",
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
            "<template><heading>First version</heading><keywords><li>custom-word</li></keywords></template>\n",
            encoding="utf-8",
        )

        weave_file = working_directory / "weave.xml"
        checked_file = working_directory / "checked.xml"
        woven = run(executable, working_directory, source_directory, "weave")
        assert woven.returncode == 0, woven.stderr
        assert not woven.stdout
        assert "<lp5-weave" in weave_file.read_text(encoding="utf-8")

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

        alternate_weave = working_directory / "alternate.xml"
        default_contents = weave_file.read_bytes()
        alternate = run(
            executable, working_directory, source_directory,
            "-w", str(alternate_weave), "weave",
        )
        assert alternate.returncode == 0 and not alternate.stdout, alternate.stderr
        assert "<lp5-weave" in alternate_weave.read_text(encoding="utf-8")
        assert weave_file.read_bytes() == default_contents

        article.write_text(
            "<template><heading>Alternate index article</heading><keywords><li>custom-word</li></keywords></template>\n",
            encoding="utf-8",
        )
        custom_output = working_directory / "custom-check.xml"
        checked = run(
            executable, working_directory, source_directory,
            "-w", str(alternate_weave), "-o", str(custom_output), "check", "1",
        )
        assert checked.returncode == 0, checked.stderr
        assert "Alternate index article" in alternate_weave.read_text(encoding="utf-8")
        assert weave_file.read_bytes() == default_contents

        searched = run(
            executable, working_directory, source_directory,
            "-w", str(alternate_weave), "search", "--", "Alternate index article",
        )
        assert searched.returncode == 0, searched.stderr
        assert "Alternate index article" in searched.stdout

        keyword_search = run(
            executable, working_directory, source_directory,
            "-w", str(alternate_weave), "search-keywords", "--", "custom-word",
        )
        assert keyword_search.returncode == 0, keyword_search.stderr
        assert "Alternate index article" in keyword_search.stdout

        listed = run(
            executable, working_directory, source_directory,
            "-w", str(alternate_weave), "list-keywords",
        )
        assert listed.returncode == 0, listed.stderr
        keywords = ET.fromstring(listed.stdout)
        assert keywords.tag == "lp5-keywords"
        assert [node.text for node in keywords] == ["custom-word"]

        # A deliberately different default index must not be read for add-article.
        weave_file.write_text("<lp5-weave><articles/><bundles/></lp5-weave>", encoding="utf-8")
        future = alternate_weave.stat().st_mtime_ns + 2_000_000_000
        os.utime(weave_file, ns=(future, future))
        new_article = working_directory / "new-article.lp5"
        new_article.write_text("<template><heading>New article</heading></template>\n",
                               encoding="utf-8")
        added = run(
            executable, working_directory, source_directory,
            "-w", str(alternate_weave), "add-article", "lp5.lp5", str(new_article),
        )
        assert added.returncode == 0, added.stderr
        assert "new-article-id:" in added.stderr
        assert ET.fromstring(added.stdout).tag == "template"
        assert weave_file.read_text(encoding="utf-8") == "<lp5-weave><articles/><bundles/></lp5-weave>"

        # A custom output option may not silently redirect a selected weave.
        conflict = run(
            executable, working_directory, source_directory,
            "-w", str(alternate_weave), "-o", str(working_directory / "conflict.xml"),
            "weave",
        )
        assert conflict.returncode == 1 and "different files" in conflict.stderr
        conflict = run(
            executable, working_directory, source_directory,
            "-w", str(alternate_weave), "-w", str(weave_file), "show-bundle",
        )
        assert conflict.returncode == 1 and "specified more than once" in conflict.stderr
        missing_option = run(
            executable, working_directory, source_directory, "show-bundle", "-w",
        )
        assert missing_option.returncode == 1 and "requires a weave file" in missing_option.stderr

        # An unsuccessful preflight must stop the requested check command.
        os.utime(alternate_weave, ns=(0, 0))
        (source_directory / "lp5.lp5").write_text("<broken", encoding="utf-8")
        not_created = working_directory / "must-not-exist.xml"
        failed = run(
            executable, working_directory, source_directory,
            "-w", str(alternate_weave), "-o", str(not_created), "check", "1",
        )
        assert failed.returncode != 0
        assert "requested command was not run" in failed.stderr
        assert not not_created.exists()

    print("weave freshness preflight test passed")


if __name__ == "__main__":
    main()
