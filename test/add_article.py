#!/usr/bin/env python3
"""Exercise the add-article command's complete source-file update."""

import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parents[1]


def write_article(directory, filename, contents):
    (directory / filename).write_text(contents, encoding="utf-8")


def main():
    if len(sys.argv) != 2:
        raise SystemExit(f"usage: {sys.argv[0]} /path/to/lp5")
    executable = str(Path(sys.argv[1]).resolve())

    with tempfile.TemporaryDirectory(prefix="lp5-add-article-cli-") as temporary:
        working = Path(temporary)
        source = working / "source"
        source.mkdir()
        for stylesheet in ("add-article.xsl", "check.xsl", "tangle.xsl", "weave.xsl"):
            (working / stylesheet).symlink_to(PROJECT_DIR / stylesheet)
        write_article(source, "lp5.lp5", """<template>
    <heading>Root article</heading>
    <children><li id="1.lp5"/><li id="2.lp5"/></children>
</template>
""")
        write_article(source, "1.lp5", "<template><heading>First</heading></template>\n")
        write_article(source, "2.lp5", "<template><heading>Second</heading></template>\n")

        weave = working / "weave.xml"

        def run(*arguments):
            return subprocess.run(
                [executable, "-s", str(source), "-w", str(weave), *arguments],
                cwd=working,
                capture_output=True,
            )

        woven = run("weave")
        assert woven.returncode == 0, woven.stderr
        original_weave = weave.read_bytes()
        incoming = working / "incoming.lp5"
        article_bytes = b'''<?xml version="1.0" encoding="UTF-8"?>
<template><heading>Inserted article</heading>
<section data-lp5-kind="code"><name>Test</name><code><![CDATA[const x = "<ok>";]]></code></section>
</template>
'''
        incoming.write_bytes(article_bytes)

        added = run("add-article", "lp5.lp5", str(incoming), "2.lp5")
        assert added.returncode == 0 and added.stdout == b"", added.stderr
        assert b"added article: 3.lp5" in added.stderr
        assert (source / "3.lp5").read_bytes() == article_bytes
        parent = ET.parse(source / "lp5.lp5").getroot()
        assert [link.get("id") for link in parent.findall("children/li")] == [
            "1.lp5", "3.lp5", "2.lp5"
        ]
        assert parent.findtext("heading") == "Root article"
        assert weave.read_bytes() == original_weave
        assert incoming.read_bytes() == article_bytes

        checked = run("check", "3.lp5")
        assert checked.returncode == 0, checked.stderr
        assert ET.parse(weave).find("articles/article[@file='3.lp5']") is not None

        before_failure = {path.name: path.read_bytes() for path in source.iterdir()}
        invalid_link = run("add-article", "lp5.lp5", str(incoming), "missing.lp5")
        assert invalid_link.returncode != 0
        assert {path.name: path.read_bytes() for path in source.iterdir()} == before_failure

        missing_input = run("add-article", "lp5.lp5", str(working / "missing.lp5"))
        assert missing_input.returncode != 0
        assert {path.name: path.read_bytes() for path in source.iterdir()} == before_failure

        output_option = run("-o", str(working / "parent.xml"), "add-article",
                            "lp5.lp5", str(incoming))
        assert output_option.returncode == 1 and b"-o is not valid" in output_option.stderr
        assert {path.name: path.read_bytes() for path in source.iterdir()} == before_failure

    print("add-article CLI installation and rollback checks passed")


if __name__ == "__main__":
    main()
