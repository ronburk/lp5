#!/usr/bin/env python3
"""Check project-derived paths and the project-name-first command syntax."""

import json
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[1]


def run(executable, working, project, *arguments):
    return subprocess.run([executable, project, *arguments], cwd=working,
                          capture_output=True, text=True)


def write_project(directory, name, code):
    project_directory = directory / f"{name}.lp5"
    project_directory.mkdir()
    root = project_directory / f"{name}.lp5"
    root.write_text(
        "<template><section data-lp5-kind=\"code\"><name></name>"
        f"<code><![CDATA[{code}]]></code></section>"
        "<children><li id=\"1.lp5\"/></children></template>\n",
        encoding="utf-8",
    )
    (project_directory / "1.lp5").write_text(
        "<template><heading>Child</heading></template>\n", encoding="utf-8"
    )
    return project_directory


def main():
    if len(sys.argv) != 2:
        raise SystemExit(f"usage: {sys.argv[0]} /path/to/lp5")
    executable = str(Path(sys.argv[1]).resolve())

    with tempfile.TemporaryDirectory(prefix="lp5-project-name-") as temporary:
        working = Path(temporary)
        for stylesheet in ("weave.xsl", "tangle.xsl"):
            (working / stylesheet).symlink_to(PROJECT_DIR / stylesheet)
        first = write_project(working, "alpha", "alpha();\n")
        second = write_project(working, "second project", "second();\n")

        for name, project, expected in (
                ("alpha", first, "alpha();"),
                ("second project", second, "second();")):
            woven = run(executable, working, name, "weave")
            assert woven.returncode == 0, woven.stderr
            cache = project / "weave.xml"
            assert cache.exists()
            woven_articles = ET.parse(cache).findall("articles/article")
            assert woven_articles[0].get("file") == f"{name}.lp5"
            assert woven_articles[0].get("parent") is None
            assert woven_articles[1].get("parent") == f"{name}.lp5"

            tangled = run(executable, working, name, "tangle")
            assert tangled.returncode == 0, tangled.stderr
            output = project / f"{name}.out"
            source_map = project / f"{name}.map"
            assert expected in output.read_text(encoding="utf-8")
            mapping = json.loads(source_map.read_text(encoding="utf-8"))
            assert mapping["version"] == 3
            assert mapping["file"] == f"{name}.lp5/{name}.out"
            assert mapping["sources"] == [f"{name}.lp5/{name}.lp5"]

        (first / "1.lp5").write_text(
            "<template><children><li id=\"alpha.lp5\"/></children></template>\n",
            encoding="utf-8",
        )
        cycle = run(executable, working, "alpha", "weave")
        assert cycle.returncode != 0
        assert "root article 'alpha.lp5' has incoming parent link" in cycle.stderr

        missing = run(executable, working, "missing", "weave")
        assert missing.returncode != 0
        assert "missing.lp5" in missing.stderr

        invalid = run(executable, working, "../alpha", "weave")
        assert invalid.returncode != 0 and "project name" in invalid.stderr

        extra_root = run(executable, working, "alpha", "weave", "other.lp5")
        assert extra_root.returncode != 0
        assert not (working / "other.lp5").exists()

        old_override = run(executable, working, "-w", "alternate.xml", "weave")
        assert old_override.returncode != 0
        assert not (working / "alternate.xml").exists()

    print("project-name CLI checks passed")


if __name__ == "__main__":
    main()
