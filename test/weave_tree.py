#!/usr/bin/env python3
"""Verify weave parent metadata and source-tree validation."""

import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[1]


def write(directory, filename, children=()):
    root = ET.Element("template")
    if children:
        links = ET.SubElement(root, "children")
        for target in children:
            ET.SubElement(links, "li", {"id": target})
    ET.ElementTree(root).write(directory / filename, encoding="utf-8", xml_declaration=True)


def run(executable, working, source):
    return subprocess.run(
        [executable, "-s", str(source), "-w", str(working / "weave.xml"), "weave"],
        cwd=working, capture_output=True, text=True,
    )


def fixture(executable, working, files):
    source = working / "source"
    source.mkdir()
    for name, children in files.items():
        write(source, name, children)
    return run(executable, working, source), source


def main():
    if len(sys.argv) != 2:
        raise SystemExit(f"usage: {sys.argv[0]} /path/to/lp5")
    executable = str(Path(sys.argv[1]).resolve())
    with tempfile.TemporaryDirectory(prefix="lp5-weave-tree-") as temporary:
        working = Path(temporary)
        source = working / "source"
        source.mkdir()
        for stylesheet in ("weave.xsl", "tangle.xsl"):
            (working / stylesheet).symlink_to(PROJECT_DIR / stylesheet)
        for name, children in {
            "lp5.lp5": ("1.lp5", "missing.lp5"),
            "1.lp5": ("2.lp5",),
            "2.lp5": (),
            "orphan.lp5": ("orphan-child.lp5",),
            "orphan-child.lp5": (),
            "single.lp5": (),
        }.items():
            write(source, name, children)
        valid = run(executable, working, source)
        assert valid.returncode == 0, valid.stderr
        assert "failed to load external entity" not in valid.stderr
        root = ET.parse(working / "weave.xml").getroot()
        articles = {article.get("file"): article for article in root.find("articles")}
        assert articles["lp5.lp5"].get("parent") is None
        assert articles["1.lp5"].get("parent") == "lp5.lp5"
        assert articles["2.lp5"].get("parent") == "1.lp5"
        assert articles["orphan.lp5"].get("parent") is None
        assert articles["orphan-child.lp5"].get("parent") == "orphan.lp5"
        assert articles["single.lp5"].get("parent") is None
        missing = articles["lp5.lp5"].find("children/child[@file='missing.lp5']")
        assert missing is not None and missing.get("status") == "missing"
        assert "missing.lp5" not in articles

        cases = [
            ({"lp5.lp5": (), "1.lp5": ("1.lp5",)}, "article '1.lp5' links to itself"),
            ({"lp5.lp5": (), "1.lp5": ("2.lp5",), "2.lp5": ("1.lp5",)}, "cycle includes article"),
            ({"lp5.lp5": ("1.lp5", "1.lp5"), "1.lp5": ()}, "article '1.lp5' has multiple parent links"),
            ({"lp5.lp5": ("1.lp5", "2.lp5"), "1.lp5": ("3.lp5",), "2.lp5": ("3.lp5",), "3.lp5": ()}, "article '3.lp5' has multiple parent links"),
            ({"lp5.lp5": (), "1.lp5": ("lp5.lp5",)}, "root article 'lp5.lp5' has incoming parent link"),
        ]
        for index, (files, diagnostic) in enumerate(cases):
            case_dir = working / f"case-{index}"
            case_dir.mkdir()
            for stylesheet in ("weave.xsl", "tangle.xsl"):
                (case_dir / stylesheet).symlink_to(PROJECT_DIR / stylesheet)
            result, _ = fixture(executable, case_dir, files)
            assert result.returncode != 0, (files, result.stdout, result.stderr)
            assert diagnostic in result.stderr, (diagnostic, result.stderr)
            assert "failed to load external entity" not in result.stderr, result.stderr

    print("weave tree checks passed")


if __name__ == "__main__":
    main()
