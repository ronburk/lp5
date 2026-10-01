#!/usr/bin/env python3
"""Check that add-article preserves parent fields and child-link order."""

import re
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parents[1]
ADD_ARTICLE_XSL = PROJECT_DIR / "add-article.xsl"
CHECK_XSL = PROJECT_DIR / "check.xsl"


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


def run_case(parent_children, before_child_id, expected_child_ids):
    with tempfile.TemporaryDirectory(prefix="lp5-add-article-") as temporary:
        directory = Path(temporary)
        articles_dir = directory / "articles"
        articles_dir.mkdir()
        for article_id in ("2.lp5", "3.lp5"):
            (articles_dir / article_id).write_text(
                "<template/>", encoding="utf-8"
            )

        weave_file, source_parent = make_weave(directory, parent_children)
        new_article = directory / "new.lp5"
        new_article.write_text(
            "<template><heading>New article</heading></template>\n",
            encoding="utf-8",
        )

        command = [
            "xsltproc",
            "--stringparam", "parent_id", "1.lp5",
            "--stringparam", "articles_dir", str(articles_dir),
            "--stringparam", "article_file", str(new_article),
        ]
        if before_child_id is not None:
            command.extend(["--stringparam", "before_child_id", before_child_id])
        command.extend([str(ADD_ARTICLE_XSL), str(weave_file)])
        result = subprocess.run(
            command,
            cwd=PROJECT_DIR,
            check=True,
            capture_output=True,
            text=True,
        )

        new_id = re.search(r"new-article-id:\s*(\S+)", result.stderr)
        assert new_id is not None, result.stderr
        assert new_id.group(1) == "4.lp5", result.stderr

        output_root = ET.fromstring(result.stdout)
        assert output_root.tag == "template"
        output_children = output_root.find("children")
        assert output_children is not None
        child_ids = [child.get("id") for child in output_children.findall("li")]
        assert child_ids == expected_child_ids, child_ids

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

        assert "<![CDATA[const markup = \"<div>\";" in result.stdout
        assert "<code>code</code>" in result.stdout

        updated_parent = directory / "updated-parent.lp5"
        updated_parent.write_text(result.stdout, encoding="utf-8")
        subprocess.run(
            [
                "xsltproc",
                "--stringparam", "article-location", str(updated_parent),
                str(CHECK_XSL),
                str(updated_parent),
            ],
            cwd=PROJECT_DIR,
            check=True,
            capture_output=True,
            text=True,
        )


def main():
    run_case(["2.lp5", "3.lp5"], None, ["4.lp5", "2.lp5", "3.lp5"])
    run_case(["2.lp5", "3.lp5"], "3.lp5", ["2.lp5", "4.lp5", "3.lp5"])
    run_case([], None, ["4.lp5"])
    run_case(None, None, ["4.lp5"])
    print("add-article preservation and child-list tests passed")


if __name__ == "__main__":
    main()
