#!/usr/bin/env python3
"""Exercise add-article stylesheet behavior through the fixed project layout."""

import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[1]


def run_case(executable, parent_children, before_child_id, expected_child_ids):
    with tempfile.TemporaryDirectory(prefix="lp5-add-article-") as temporary:
        working = Path(temporary)
        source = working / "articles.lp5"
        source.mkdir()
        for stylesheet in ("add-article.xsl", "tangle.xsl", "weave.xsl"):
            (working / stylesheet).symlink_to(PROJECT_DIR / stylesheet)
        (source / "articles.lp5").write_text(
            "<template><children><li id=\"1.lp5\"/></children></template>\n", encoding="utf-8")
        for article_id in ("2.lp5", "3.lp5"):
            (source / article_id).write_text(
                "<template><heading>Existing article</heading></template>\n",
                encoding="utf-8",
            )
        (source / "1.lp5").write_text(
            "<template><heading>Parent article</heading><keywords>\n"
            "<li>preserve me</li><li>and me</li></keywords>\n"
            "<section data-lp5-kind=\"explanation\"><p>Inline "
            "<code>code</code> stays.</p></section>\n"
            "<section data-lp5-kind=\"code\"><name>Example</name>"
            "<code><![CDATA[const markup = \"<div>\";]]></code></section>"
            "<children>" + "".join(f"<li id=\"{child}\"/>" for child in (parent_children or [])) +
            "</children></template>\n", encoding="utf-8")
        occupied = source / "4.lp5"
        occupied_contents = b"<this is malformed XML"
        occupied.write_bytes(occupied_contents)

        new_article = working / "new.lp5"
        new_article.write_text(
            "<template><heading>New article</heading></template>\n",
            encoding="utf-8",
        )
        result = subprocess.run(
            [executable, "articles", "add-article", "1.lp5",
             str(new_article), *([before_child_id] if before_child_id else [])],
            cwd=working, capture_output=True, text=True,
        )
        assert result.returncode == 0, result.stderr
        assert not result.stdout
        assert "added article: 5.lp5" in result.stderr, result.stderr
        assert "failed to load external entity" not in result.stderr
        assert occupied.read_bytes() == occupied_contents
        assert (source / "5.lp5").read_bytes() == new_article.read_bytes()

        output = ET.parse(source / "1.lp5").getroot()
        children = output.find("children")
        child_ids = [] if children is None else [n.get("id") for n in children.findall("li")]
        assert child_ids == expected_child_ids, child_ids
        assert child_ids.count("5.lp5") == 1
        output_fields = [node.tag for node in output if node.tag != "children"]
        assert output_fields == ["heading", "keywords", "section", "section"]
        assert output.findtext("heading") == "Parent article"
        assert [n.text for n in output.findall("keywords/li")] == ["preserve me", "and me"]
        text = (source / "1.lp5").read_text(encoding="utf-8")
        assert "<![CDATA[const markup = \"<div>\";" in text
        assert "<code>code</code>" in text


def main():
    if len(sys.argv) != 2:
        raise SystemExit(f"usage: {sys.argv[0]} /path/to/lp5")
    executable = str(Path(sys.argv[1]).resolve())
    run_case(executable, ["2.lp5", "3.lp5"], None, ["5.lp5", "2.lp5", "3.lp5"])
    run_case(executable, ["2.lp5", "3.lp5"], "3.lp5", ["2.lp5", "5.lp5", "3.lp5"])
    run_case(executable, [], None, ["5.lp5"])
    run_case(executable, None, None, ["5.lp5"])
    print("add-article preservation, ordering, and filename tests passed")


if __name__ == "__main__":
    main()
