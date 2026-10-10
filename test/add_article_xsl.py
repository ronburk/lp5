#!/usr/bin/env python3
"""Exercise add-article stylesheet behavior through the lp5 launcher."""

import os
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parents[1]


def element_value(element):
    """Return a tree value that ignores only the element's own tail."""
    return (
        element.tag,
        tuple(sorted(element.attrib.items())),
        element.text,
        tuple((element_value(child), child.tail) for child in element),
    )


def make_weave(directory, parent_children):
    root = ET.Element("lp5-weave", {"version": "1"})
    articles = ET.SubElement(root, "articles")
    parent = ET.SubElement(articles, "article", {"file": "1.lp5"})
    ET.SubElement(parent, "heading").text = "Parent article"

    keywords = ET.SubElement(parent, "keywords")
    ET.SubElement(keywords, "li").text = "preserve me"
    ET.SubElement(keywords, "li").text = "and me"

    explanation = ET.SubElement(
        parent, "section", {"data-lp5-kind": "explanation"}
    )
    paragraph = ET.SubElement(explanation, "p")
    paragraph.text = "Inline "
    ET.SubElement(paragraph, "code").text = "code"
    ET.SubElement(paragraph, "em").text = " stays"
    paragraph[-1].tail = "."

    code_section = ET.SubElement(
        parent, "section", {"data-lp5-kind": "code"}
    )
    ET.SubElement(code_section, "name").text = "Example"
    code = ET.SubElement(code_section, "code")
    code.text = 'const markup = "<div>";\n'
    ET.SubElement(code, "lp5-", {"ref": "helper"}).tail = "\n"

    if parent_children is not None:
        children = ET.SubElement(parent, "children")
        for child_id in parent_children:
            ET.SubElement(
                children, "child", {"file": child_id, "status": "available"}
            )

    for article_id in ("2.lp5", "3.lp5"):
        article = ET.SubElement(articles, "article", {"file": article_id})
        ET.SubElement(article, "heading").text = f"Article {article_id}"

    ET.indent(root, space="    ")
    weave_file = directory / "weave.xml"
    ET.ElementTree(root).write(
        weave_file, encoding="utf-8", xml_declaration=True
    )
    return weave_file, parent


def run_case(executable, parent_children, before_child_id, expected_child_ids):
    with tempfile.TemporaryDirectory(prefix="lp5-add-article-") as temporary:
        directory = Path(temporary)
        articles_dir = directory / "articles"
        articles_dir.mkdir()
        parent_source = ET.Element("template")
        if parent_children is not None:
            children = ET.SubElement(parent_source, "children")
            for child_id in parent_children:
                ET.SubElement(children, "li", {"id": child_id})
        ET.ElementTree(parent_source).write(
            articles_dir / "1.lp5", encoding="utf-8", xml_declaration=True
        )
        for article_id in ("2.lp5", "3.lp5"):
            (articles_dir / article_id).write_text(
                "<template><heading>Existing article</heading></template>\n",
                encoding="utf-8",
            )

        occupied_candidate = articles_dir / "4.lp5"
        occupied_contents = b"<this is malformed XML"
        occupied_candidate.write_bytes(occupied_contents)

        weave_file, source_parent = make_weave(directory, parent_children)
        future_time = max(
            weave_file.stat().st_mtime_ns,
            articles_dir.stat().st_mtime_ns,
            occupied_candidate.stat().st_mtime_ns,
        ) + 1_000_000_000
        os.utime(weave_file, ns=(future_time, future_time))
        new_article = directory / "new.lp5"
        new_article.write_text(
            "<template><heading>New article</heading></template>\n",
            encoding="utf-8",
        )

        command = [
            executable,
            "-s", str(articles_dir),
            "-w", str(weave_file),
            "add-article", "1.lp5", str(new_article),
        ]
        if before_child_id is not None:
            command.append(before_child_id)
        result = subprocess.run(
            command,
            cwd=PROJECT_DIR,
            check=True,
            capture_output=True,
            text=True,
        )

        assert not result.stdout
        assert "added article: 5.lp5" in result.stderr, result.stderr
        assert "failed to load external entity" not in result.stderr, result.stderr
        assert occupied_candidate.read_bytes() == occupied_contents
        assert (articles_dir / "5.lp5").read_bytes() == new_article.read_bytes()

        output_root = ET.parse(articles_dir / "1.lp5").getroot()
        output_children = output_root.find("children")
        assert output_children is not None
        child_ids = [child.get("id") for child in output_children.findall("li")]
        assert child_ids == expected_child_ids, child_ids
        assert child_ids.count("5.lp5") == 1, child_ids

        source_fields = [
            element_value(element)
            for element in source_parent
            if element.tag != "children"
        ]
        output_fields = [
            element_value(element)
            for element in output_root
            if element.tag != "children"
        ]
        assert output_fields == source_fields

        output_text = (articles_dir / "1.lp5").read_text(encoding="utf-8")
        assert "<![CDATA[const markup = \"<div>\";" in output_text
        assert "<code>code</code>" in output_text


def main():
    if len(sys.argv) != 2:
        raise SystemExit(f"usage: {sys.argv[0]} /path/to/lp5")
    executable = str(Path(sys.argv[1]).resolve())

    run_case(executable, ["2.lp5", "3.lp5"], None,
             ["5.lp5", "2.lp5", "3.lp5"])
    run_case(executable, ["2.lp5", "3.lp5"], "3.lp5",
             ["2.lp5", "5.lp5", "3.lp5"])
    run_case(executable, [], None, ["5.lp5"])
    run_case(executable, None, None, ["5.lp5"])
    print("add-article preservation, ordering, and filename tests passed")


if __name__ == "__main__":
    main()
