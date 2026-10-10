#!/usr/bin/env python3
"""Verify the compiled keyword index through the production weave command."""

import os
import re
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parents[1]
ASCII_LOWER = str.maketrans("ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz")


def canonical(value):
    return re.sub(r"[ \t\r\n]+", " ", value).strip(" ").translate(ASCII_LOWER)


def write_article(directory, filename, terms=None, children=(), bundle=None):
    root = ET.Element("template")
    if children:
        links = ET.SubElement(root, "children")
        for child in children:
            ET.SubElement(links, "li", {"id": child})
    if terms is not None:
        keywords = ET.SubElement(root, "keywords")
        for term in terms:
            ET.SubElement(keywords, "li").text = term
    if bundle is not None:
        section = ET.SubElement(root, "section", {"data-lp5-kind": "code"})
        ET.SubElement(section, "name").text = bundle
        ET.SubElement(section, "code")
    # These names are legal explanatory markup, but are not article metadata.
    explanation = ET.SubElement(root, "section", {"data-lp5-kind": "explanation"})
    nested = ET.SubElement(ET.SubElement(explanation, "articles"), "article")
    ET.SubElement(ET.SubElement(nested, "keywords"), "li").text = "explanation-only"
    ET.ElementTree(root).write(directory / filename, encoding="utf-8", xml_declaration=True)


def run(executable, working, source, *arguments):
    result = subprocess.run([executable, "-s", str(source), *arguments],
                            cwd=working, capture_output=True)
    assert result.returncode == 0, result.stderr.decode("utf-8")
    return result


def check_index(document, terms_by_file, order):
    assert document.tag == "lp5-weave"
    assert [child.tag for child in document] == ["articles", "bundles", "keyword-index"]
    article_order = [a.attrib["file"] for a in document.find("articles")]
    assert article_order == order, (article_order, order)
    articles = {a.attrib["file"]: a for a in document.find("articles")}
    assert "parent" not in articles["lp5.lp5"].attrib
    if "9.lp5" in articles:
        assert articles["9.lp5"].attrib["parent"] == "lp5.lp5"
        assert articles["7.lp5"].attrib["parent"] == "9.lp5"
        assert articles["2.lp5"].attrib["parent"] == "lp5.lp5"
        for filename in order[4:]:
            assert "parent" not in articles[filename].attrib
    expected = {}
    for filename in order:
        for value in dict.fromkeys(canonical(t) for t in terms_by_file[filename]):
            if value:
                expected.setdefault(value, []).append(filename)
    actual = {}
    for keyword in document.find("keyword-index"):
        assert keyword.tag == "keyword" and set(keyword.attrib) == {"value"}
        value = keyword.attrib["value"]
        assert value not in actual
        actual[value] = []
        for article in keyword:
            assert article.tag == "article" and set(article.attrib) == {"file"}
            assert len(article) == 0
            actual[value].append(article.attrib["file"])
    assert actual == expected, (actual, expected)
    assert "explanation-only" not in actual


def main():
    if len(sys.argv) != 2:
        raise SystemExit(f"usage: {sys.argv[0]} /path/to/lp5")
    executable = str(Path(sys.argv[1]).resolve())
    with tempfile.TemporaryDirectory(prefix="lp5-keyword-index-") as temporary:
        working = Path(temporary)
        source = working / "source"
        source.mkdir()
        for stylesheet in ("weave.xsl", "tangle.xsl", "check.xsl"):
            (working / stylesheet).symlink_to(PROJECT_DIR / stylesheet)

        special = "</keyword> & \"quoted\", article O'Reilly"
        terms = {
            "lp5.lp5": [" Shared ", "save\t article", "Z-key", " "],
            "9.lp5": ["SHARED", "shared", "save\n\rarticle", special, "A-key"],
            "7.lp5": [],
            "2.lp5": ["shared", "b-key", "ÉTÉ", "été", "雪", "\u00a0Shared\u00a0"],
            "0.lp5": [],
            "a&z.lp5": ["-s", "-o", "-m", "--all", "--", "heading",
                           "article", "__CODE_NAME_PARAMETER_REQUIRED__", special],
        }
        for number in range(30, 55):
            terms[f"{number}.lp5"] = ["shared"]
        for filename, keywords in terms.items():
            children = {"lp5.lp5": ("9.lp5", "2.lp5"),
                        "9.lp5": ("7.lp5",)}.get(filename, ())
            write_article(source, filename, None if filename == "0.lp5" else keywords,
                          children, "Bundle" if filename in ("9.lp5", "2.lp5") else None)
        order = ["lp5.lp5", "9.lp5", "7.lp5", "2.lp5", "0.lp5"]
        order += [f"{n}.lp5" for n in range(30, 55)] + ["a&z.lp5"]
        original = {p.name: p.read_bytes() for p in source.iterdir()}

        result = run(executable, working, source, "weave")
        assert result.stdout == b""
        document = ET.parse(working / "weave.xml").getroot()
        check_index(document, terms, order)
        values = [k.attrib["value"] for k in document.find("keyword-index")]
        assert [v for v in values if v in ("a-key", "b-key", "z-key")] == ["a-key", "b-key", "z-key"]
        assert len(document.find("keyword-index/keyword[@value='shared']")) == 28
        assert [s.attrib["article"] for s in document.find("bundles/bundle")] == ["9.lp5", "2.lp5"]
        for article in document.find("articles"):
            stored = article.find("keywords")
            original_keywords = ET.fromstring(original[article.attrib["file"]]).find("keywords")
            assert (stored is None) == (original_keywords is None)
            if stored is not None:
                assert [li.text for li in stored] == [li.text for li in original_keywords]

        result = run(executable, working, source, "weave", "-o", "weave.xml")
        assert result.stdout == b""
        check_index(ET.parse(working / "weave.xml").getroot(), terms, order)
        assert {p.name: p.read_bytes() for p in source.iterdir()} == original

        terms["9.lp5"] = ["changed keyword"]
        write_article(source, "9.lp5", terms["9.lp5"], ("7.lp5",), "Bundle")
        os.utime(working / "weave.xml", ns=(0, 0))
        edited = {p.name: p.read_bytes() for p in source.iterdir()}
        run(executable, working, source, "check", "9")
        check_index(ET.parse(working / "weave.xml").getroot(), terms, order)
        assert {p.name: p.read_bytes() for p in source.iterdir()} == edited

        empty_source = working / "empty"
        empty_source.mkdir()
        write_article(empty_source, "lp5.lp5", ["\t\n\r "])
        result = run(executable, working, empty_source, "weave")
        assert result.stdout == b""
        check_index(ET.parse(working / "weave.xml").getroot(),
                    {"lp5.lp5": [" "]}, ["lp5.lp5"])
    print("weave keyword index checks passed")


if __name__ == "__main__":
    main()
