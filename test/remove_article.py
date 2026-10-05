#!/usr/bin/env python3
"""Exercise remove-article success, refusal, and weave freshness behavior."""

import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parents[1]


def write_article(directory, filename, content):
    path = directory / filename
    path.write_text(content, encoding="utf-8")
    return path


def main():
    if len(sys.argv) != 2:
        raise SystemExit(f"usage: {sys.argv[0]} /path/to/lp5")
    executable = str(Path(sys.argv[1]).resolve())

    with tempfile.TemporaryDirectory(prefix="lp5-remove-article-") as temporary:
        working = Path(temporary)
        source = working / "source"
        source.mkdir()
        for stylesheet in (
            "weave.xsl", "tangle.xsl", "add-article.xsl", "remove-article.xsl",
            "check.xsl", "show-article.xsl", "show-bundle.xsl",
        ):
            (working / stylesheet).symlink_to(PROJECT_DIR / stylesheet)

        write_article(source, "lp5.lp5", """<template>
  <heading>Root heading</heading>
  <keywords><li>keep this</li></keywords>
  <section data-lp5-kind="explanation"><p>Keep <code>inline</code> markup.</p></section>
  <section data-lp5-kind="code"><name>Example</name><code><![CDATA[if (a < b) return "yes";
]]></code></section>
  <children><li id="1.lp5"/><li id="2.lp5"/></children>
</template>
""")
        write_article(source, "1.lp5", "<template><heading>Has child</heading><children><li id=\"3.lp5\"/><li id=\"4.lp5\"/></children></template>\n")
        write_article(source, "2.lp5", "<template><heading>Remove me</heading></template>\n")
        write_article(source, "3.lp5", "<template><heading>Grandchild</heading></template>\n")
        write_article(source, "4.lp5", "<template><heading>Sibling leaf</heading></template>\n")
        write_article(source, "orphan.lp5", "<template><heading>Orphan</heading></template>\n")

        def run(*arguments):
            return subprocess.run(
                [executable, "-s", str(source), "-w", str(working / "weave.xml"), *arguments],
                cwd=working,
                capture_output=True,
                text=True,
            )

        initial = run("weave")
        assert initial.returncode == 0, initial.stderr
        weave_before_remove = (working / "weave.xml").read_bytes()

        result = run("remove-article", "3.lp5")
        assert result.returncode == 0, result.stderr
        assert not (source / "3.lp5").exists()
        assert (working / "weave.xml").read_bytes() == weave_before_remove
        nested_parent = ET.parse(source / "1.lp5").getroot()
        assert [node.get("id") for node in nested_parent.findall("children/li")] == ["4.lp5"]

        # The next removal refreshes the selected weave against the current source.
        result = run("remove-article", "2.lp5")
        assert result.returncode == 0, result.stderr
        assert not (source / "2.lp5").exists()
        updated = ET.parse(source / "lp5.lp5").getroot()
        assert [node.get("id") for node in updated.findall("children/li")] == ["1.lp5"]
        assert updated.findtext("heading") == "Root heading"
        assert [node.text for node in updated.findall("keywords/li")] == ["keep this"]
        assert updated.find("section[@data-lp5-kind='explanation']/p/code").text == "inline"
        assert updated.findtext("section[@data-lp5-kind='code']/name") == "Example"
        assert updated.findtext("section[@data-lp5-kind='code']/code") == 'if (a < b) return "yes";\n'
        assert run("check", str(source / "lp5.lp5")).returncode == 0

        # The command leaves its index alone; the next ordinary command refreshes it.
        refreshed = run("show-article", "lp5.lp5")
        assert refreshed.returncode == 0, refreshed.stderr
        refreshed_weave = ET.parse(working / "weave.xml").getroot()
        assert refreshed_weave.find("articles/article[@file='2.lp5']") is None

        # Each refusal leaves every source file byte-for-byte unchanged.
        for article_id, message in (
            ("lp5.lp5", "root article"),
            ("1.lp5", "has children"),
            ("orphan.lp5", "parent link"),
            ("missing.lp5", "must exist"),
        ):
            before = {path.name: path.read_bytes() for path in source.iterdir()}
            result = run("remove-article", article_id)
            assert result.returncode == 1, (article_id, result.stdout, result.stderr)
            assert message in result.stderr, (article_id, result.stderr)
            assert {path.name: path.read_bytes() for path in source.iterdir()} == before

        before = {path.name: path.read_bytes() for path in source.iterdir()}
        result = run("remove-article", "3.lp5", "extra")
        assert result.returncode == 1 and "Usage:" in result.stderr
        result = run("-o", str(working / "unused.xml"), "remove-article", "3.lp5")
        assert result.returncode == 1 and "-o is not valid" in result.stderr
        assert {path.name: path.read_bytes() for path in source.iterdir()} == before

    print("remove-article CLI tests passed")


if __name__ == "__main__":
    main()
