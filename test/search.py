#!/usr/bin/env python3
"""Acceptance checks for literal full-text article search."""

import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parents[1]


def article(source, filename, heading=None, keywords=(), explanation=None,
            code_name=None, code=None, children=()):
    root = ET.Element("template")
    if children:
        links = ET.SubElement(root, "children")
        for child in children:
            ET.SubElement(links, "li", {"id": child})
    if heading is not None:
        ET.SubElement(root, "heading").text = heading
    if keywords:
        keyword_list = ET.SubElement(root, "keywords")
        for value in keywords:
            ET.SubElement(keyword_list, "li").text = value
    if explanation is not None:
        section = ET.SubElement(root, "section", {"data-lp5-kind": "explanation"})
        paragraph = ET.SubElement(section, "p")
        if isinstance(explanation, tuple):
            paragraph.text = explanation[0]
            emphasis = ET.SubElement(paragraph, "em")
            emphasis.text = explanation[1]
            emphasis.tail = explanation[2]
        else:
            paragraph.text = explanation
    if code_name is not None:
        section = ET.SubElement(root, "section", {"data-lp5-kind": "code"})
        ET.SubElement(section, "name").text = code_name
        ET.SubElement(section, "code").text = code or ""
    ET.ElementTree(root).write(source / filename, encoding="utf-8", xml_declaration=True)


def result_map(result):
    return {
        (match.attrib["term"], match.attrib["field"]): match.find("excerpt")
        for match in result.findall("matches/match")
    }


def main():
    if len(sys.argv) != 2:
        raise SystemExit(f"usage: {sys.argv[0]} /path/to/lp5")
    executable = str(Path(sys.argv[1]).resolve())
    with tempfile.TemporaryDirectory(prefix="lp5-search-") as temporary:
        working = Path(temporary)
        source = working / "source"
        source.mkdir()
        for stylesheet in ("weave.xsl", "tangle.xsl", "check.xsl", "search.xsl"):
            (working / stylesheet).symlink_to(PROJECT_DIR / stylesheet)

        article(source, "lp5.lp5", heading='Say "hi" & <xml>', keywords=("common marker",),
                explanation="We save article text, and the literal -o option.",
                code_name="mainBundle", code="root_function();",
                children=("3.lp5", "1.lp5"))
        article(source, "3.lp5", heading="Storage for articles", keywords=("draft & notes",),
                explanation=("Before Save ", "article", " safely, reload the article."),
                code_name="ioStore", code='save_article("draft & notes");')
        article(source, "1.lp5", heading="save", explanation="article")
        article(source, "5.lp5", explanation="z" * 300 + "end needle")
        long_explanation = "x" * 240 + "unique needle" + "y" * 240
        article(source, "4.lp5", explanation=long_explanation)
        article(source, "6.lp5", heading="priorityneedle priorityneedle",
                keywords=("  PRIORITYNEEDLE  ", "priorityneedle topic"),
                code_name="ranking", code="priorityneedle secondaryneedle")
        article(source, "7.lp5", explanation="priorityneedle priorityneedle")
        article(source, "8.lp5", keywords=("priorityneedle",))
        for number in range(20, 45):
            article(source, f"{number}.lp5", explanation="shared marker in an orphan article")
        original = {path.name: path.read_bytes() for path in source.iterdir()}

        def run(*args):
            return subprocess.run([executable, "-s", str(source), *args], cwd=working,
                                  capture_output=True)

        def search(terms, all_terms=False):
            args = ["search"]
            if all_terms:
                args.append("--all")
            args.extend(["--", *terms])
            process = run(*args)
            assert process.returncode == 0, process.stderr
            assert process.stdout.endswith(b"\n")
            root = ET.fromstring(process.stdout)
            assert root.tag == "lp5-search"
            assert root.attrib["mode"] == ("all" if all_terms else "any")
            assert [node.tag for node in root] == ["query", "results"]
            assert [node.text for node in root.find("query")] == list(dict.fromkeys(
                " ".join(value.split()).translate(str.maketrans(
                    "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"))
                for value in terms))
            assert int(root.attrib["total"]) == len(root.findall("results/article"))
            return root

        phrase = search(["SAVE\t article"])
        phrase_results = phrase.findall("results/article")
        assert [node.attrib["file"] for node in phrase_results] == ["lp5.lp5", "3.lp5"]
        assert phrase_results[0].attrib["score"] == "1"
        assert list(result_map(phrase_results[0])) == [("save article", "explanation")]
        assert list(result_map(phrase_results[1])) == [("save article", "explanation")]
        assert len(phrase_results[0].find("matches/match/excerpt")) == 0
        # A phrase may cross inline markup, but it cannot cross article fields.
        assert all(node.attrib["file"] != "1.lp5" for node in phrase_results)

        for match in phrase_results[0].findall("matches/match"):
            excerpt = match.find("excerpt")
            assert excerpt.attrib == {"truncated-before": "false", "truncated-after": "false"}
            assert excerpt.text == "We save article text, and the literal -o option."
        at_start = search(['say "hi"']).find("results/article/matches/match/excerpt")
        assert at_start.attrib["truncated-before"] == "false"
        assert not at_start.text.startswith("…")
        at_end = search(["end needle"]).find("results/article/matches/match/excerpt")
        assert at_end.attrib == {"truncated-before": "true", "truncated-after": "false"}
        assert at_end.text.startswith("…") and at_end.text.endswith("end needle")

        both = search(["save", "reload", "SAVE"], all_terms=True)
        both_results = both.findall("results/article")
        assert [node.attrib["file"] for node in both_results] == ["3.lp5"]
        assert both_results[0].attrib["score"] == "2"
        assert [match.attrib["term"] for match in both_results[0].findall("matches/match")] == [
            "save", "save", "reload"]

        fields = search(["iostore", "draft & notes"], all_terms=True)
        article3 = fields.find("results/article")
        assert article3.attrib == {"file": "3.lp5", "score": "3"}
        matches = result_map(article3)
        assert set(matches) == {
            ("iostore", "code-name"),
            ("draft & notes", "keyword"),
            ("draft & notes", "code"),
        }
        assert "ioStore" in matches[("iostore", "code-name")].text

        ranked = search(["priorityneedle", " PRIORITYNEEDLE "]).findall("results/article")
        assert [(node.attrib["file"], node.attrib["score"]) for node in ranked] == [
            ("6.lp5", "2"), ("8.lp5", "2"), ("7.lp5", "1")]
        assert {match.attrib["field"] for match in ranked[0].findall("matches/match")} == {
            "heading", "keyword", "code"}
        mixed = search(["priorityneedle", "secondaryneedle"], all_terms=True)
        assert [node.attrib for node in mixed.findall("results/article")] == [
            {"file": "6.lp5", "score": "3"}]

        literal_options = search(["-o", "save article"], all_terms=True)
        assert [node.attrib["file"] for node in literal_options.findall("results/article")] == ["lp5.lp5"]
        escaped = search(['say "hi" & <xml>'])
        assert escaped.find("query/term").text == 'say "hi" & <xml>'
        assert escaped.find("results/article").attrib["file"] == "lp5.lp5"

        excerpt_result = search(["unique needle"]).find("results/article")
        assert excerpt_result.attrib["file"] == "4.lp5"
        excerpt = excerpt_result.find("matches/match/excerpt")
        assert excerpt.attrib == {"truncated-before": "true", "truncated-after": "true"}
        assert "unique needle" in excerpt.text
        assert len(excerpt.text) <= 202

        no_cap = search(["shared marker"])
        assert len(no_cap.findall("results/article")) == 25
        assert no_cap.findall("results/article")[-1].attrib["file"] == "44.lp5"
        ordinary = run("search", "foo")
        assert ordinary.returncode == 0, ordinary.stderr
        assert ET.fromstring(ordinary.stdout).attrib["total"] == "0"
        assert search(["absent phrase"]).attrib["total"] == "0"
        assert {path.name: path.read_bytes() for path in source.iterdir()} == original

        output = working / "results.xml"
        redirected = run("-o", str(output), "search", "--all", "--", "save", "reload")
        assert redirected.returncode == 0 and redirected.stdout == b"", redirected.stderr
        assert ET.parse(output).getroot().find("results/article").attrib["file"] == "3.lp5"

        for arguments in ([], ["--"], ["--all", "--"], ["--other", "--", "save"],
                          ["--all", "--all", "--", "save"], ["--", " \t\r\n"]):
            failed = run("search", *arguments)
            assert failed.returncode == 1 and failed.stdout == b"" and failed.stderr, arguments
        for invalid in (b"\xff", b"\xc0\x80", b"\x01"):
            failed = run("search", "--", invalid)
            assert failed.returncode == 1 and failed.stdout == b"" and failed.stderr
        if Path("/dev/full").exists():
            failed = run("-o", "/dev/full", "search", "--", "save")
            assert failed.returncode == 1 and failed.stderr

    print("search acceptance checks passed")


if __name__ == "__main__":
    main()
