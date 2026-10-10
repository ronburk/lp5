#!/usr/bin/env python3
"""Check the keyword-search CLI contract by parsing XML from real invocations."""

import os
import re
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parents[1]
ASCII_LOWER = str.maketrans("ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz")


def normalize(text):
    return re.sub(r"[ \t\r\n]+", " ", text).strip(" ")


def canonical(text):
    return normalize(text).translate(ASCII_LOWER)


def write_article(source, filename, keywords=None, children=(), heading=None,
                  code_name=None, explanation=None):
    root = ET.Element("template")
    if children:
        links = ET.SubElement(root, "children")
        for child in children:
            ET.SubElement(links, "li", {"id": child})
    if keywords is not None:
        terms = ET.SubElement(root, "keywords")
        for keyword in keywords:
            ET.SubElement(terms, "li").text = keyword
    if heading is not None:
        root.append(ET.fromstring("<heading>" + heading + "</heading>"))
    if code_name is not None:
        section = ET.SubElement(root, "section", {"data-lp5-kind": "code"})
        section.append(ET.fromstring("<name>" + code_name + "</name>"))
        ET.SubElement(section, "code")
    if explanation is not None:
        section = ET.SubElement(root, "section", {"data-lp5-kind": "explanation"})
        section.append(ET.fromstring("<p>" + explanation + "</p>"))
    ET.ElementTree(root).write(source / filename, encoding="utf-8", xml_declaration=True)


def snapshot(source):
    return {p.name: p.read_bytes() for p in source.iterdir()}


def check_result(data, mode, terms, source, order):
    assert data.endswith(b"\n")
    root = ET.fromstring(data)
    query = list(dict.fromkeys(canonical(t) for t in terms))
    assert root.tag == "lp5-keyword-search"
    assert [child.tag for child in root] == ["query", "results"]
    assert root.find("query").attrib == {}
    assert root.find("results").attrib == {}
    assert [k.text for k in root.find("query")] == query
    expected = []
    for filename in order:
        article = ET.parse(source / filename).getroot()
        stored = {canonical(li.text or "") for li in article.findall("keywords/li")}
        matched = [term for term in query if term in stored]
        if not matched or (mode == "all" and len(matched) != len(query)):
            continue
        result = ET.Element("article", {"file": filename, "score": str(len(matched))})
        matches = ET.SubElement(result, "matched-keywords")
        for term in matched:
            ET.SubElement(matches, "keyword").text = term
        for path, tag in (("heading", "heading"),
                          ("section[@data-lp5-kind='code']/name", "code-name"),
                          ("section[@data-lp5-kind='explanation']", "excerpt")):
            node = article.find(path)
            if node is not None:
                text = normalize("".join(node.itertext()))
                scalar = ET.SubElement(result, tag)
                if tag == "excerpt":
                    scalar.set("truncated", "true" if len(text) > 200 else "false")
                    text = text[:200]
                scalar.text = text or None
        expected.append(result)
    expected.sort(key=lambda a: -int(a.attrib["score"]))
    assert root.attrib == {"version": "1", "mode": mode, "total": str(len(expected))}
    actual = list(root.find("results"))
    assert len(actual) == len(expected)
    for got, want in zip(actual, expected):
        assert got.tag == "article" and got.attrib == want.attrib, (got.attrib, want.attrib)
        assert [n.tag for n in got] == [n.tag for n in want]
        assert got.find("matched-keywords").attrib == {}
        assert [n.text for n in got.find("matched-keywords")] == [n.text for n in want.find("matched-keywords")]
        for n in got.find("matched-keywords"):
            assert n.tag == "keyword" and not n.attrib and len(n) == 0
        for n, e in zip(list(got)[1:], list(want)[1:]):
            assert len(n) == 0 and n.attrib == e.attrib and n.text == e.text, (ET.tostring(n), ET.tostring(e))
    for n in root.find("query"):
        assert n.tag == "keyword" and not n.attrib and len(n) == 0
    return root


def main():
    if len(sys.argv) != 2:
        raise SystemExit(f"usage: {sys.argv[0]} /path/to/lp5")
    executable = str(Path(sys.argv[1]).resolve())
    with tempfile.TemporaryDirectory(prefix="lp5-search-keywords-") as temporary:
        working = Path(temporary)
        source = working / "source"
        source.mkdir()
        for stylesheet in ("search-keywords.xsl", "weave.xsl", "tangle.xsl", "check.xsl",
                           "show-bundle.xsl", "add-article.xsl"):
            (working / stylesheet).symlink_to(PROJECT_DIR / stylesheet)

        special = ["O'Reilly, C++", "</keyword> & \"quoted\", article", "both ' and \"",
                   "article", "heading", "all", "__CODE_NAME_PARAMETER_REQUIRED__",
                   "-s", "-o", "-m", "--all", "--limit", "--", "雪", "ÉTÉ", "été", "\u00a0",
                   "&amp;", "&not-an-entity;", "café", "cafe\u0301", "😀"]
        write_article(source, "lp5.lp5", ["persistence"], ("3.lp5", "1.lp5", "2.lp5"), heading="Root")
        write_article(source, "3.lp5", [" Persistence ", "SAVE\t ARTICLE", "persistence", " "],
                      heading="Saving <b>&amp;</b> reloading", code_name="io<i>Store</i> &amp; More",
                      explanation="First<b>Second</b>  &amp;\t third.")
        write_article(source, "1.lp5", ["save\r\n article"], heading="", code_name="", explanation="")
        write_article(source, "2.lp5", explanation="persistence appears here but is not a keyword")
        write_article(source, "0.lp5", ["persistence"], explanation="é" * 199)
        write_article(source, "4.lp5", ["persistence"], explanation="😀" * 200)
        write_article(source, "5.lp5", ["persistence"], explanation="雪" * 201)
        write_article(source, "6.lp5", [])
        for number in range(30, 55):
            write_article(source, f"{number}.lp5", ["persistence"], heading=f"Orphan {number}")
        write_article(source, "a&z.lp5", special + ["persistence"])
        order = ["lp5.lp5", "3.lp5", "1.lp5", "2.lp5", "0.lp5", "4.lp5", "5.lp5", "6.lp5"]
        order += [f"{n}.lp5" for n in range(30, 55)] + ["a&z.lp5"]
        original = snapshot(source)

        def run(*args, env=None, source_option=True):
            arguments = [executable]
            if source_option:
                arguments += ["-s", str(source)]
            return subprocess.run(arguments + list(args), cwd=working,
                                  env=env, capture_output=True)

        def search(terms, all_terms=False):
            result = run("search-keywords", *(["--all"] if all_terms else []), "--", *terms)
            assert result.returncode == 0, result.stderr
            return check_result(result.stdout, "all" if all_terms else "any", terms, source, order)

        terms = ["PERSISTENCE", " save\t article ", "persistence"]
        result = search(terms)
        returned = result.find("results")
        assert len(returned) > 20 and returned[-1].attrib["file"] == "a&z.lp5"
        assert returned[0].attrib == {"file": "3.lp5", "score": "2"}
        assert len(search(terms, True).find("results")) == 1
        assert len(search(["save"]).find("results")) == 0
        assert len(search(["no matching keyword"]).find("results")) == 0
        search(special, True)
        search(["ÉTÉ", "été", "ÉTÉ"], True)
        assert len(search(["Été"]).find("results")) == 0
        assert snapshot(source) == original

        bundle = run("show-bundle", "weave.xml", "ioStore & More")
        assert bundle.returncode == 0, bundle.stderr
        bundle_root = ET.fromstring(bundle.stdout)
        assert bundle_root.attrib == {"name": "ioStore & More"}
        assert [s.attrib["article"] for s in bundle_root] == ["3.lp5"]
        incoming = working / "incoming.xml"
        incoming.write_text("<template><heading>New article</heading></template>")
        added = run("add-article", "weave.xml", "lp5.lp5", str(incoming))
        assert added.returncode == 0 and added.stdout == b"", added.stderr
        new_id = re.search(rb"added article: (\S+)", added.stderr)
        assert new_id is not None, added.stderr
        new_id = new_id.group(1).decode("ascii")
        parent = ET.parse(source / "lp5.lp5").getroot()
        links = [li.attrib["id"] for li in parent.findall("children/li")]
        assert len(links) == 4 and links == [new_id, "3.lp5", "1.lp5", "2.lp5"]
        assert parent.find("heading").text == "Root"
        assert (source / new_id).read_bytes() == incoming.read_bytes()
        assert all((source / name).read_bytes() == contents
                   for name, contents in original.items() if name != "lp5.lp5")

        literal = ["-o", "do-not-create.xml", "-s", "missing-directory", "-m", "do-not-create.map",
                   "--all", "--limit", "--"]
        search(literal)
        assert not (working / "do-not-create.xml").exists()
        assert not (working / "do-not-create.map").exists()

        destination = working / "matches.xml"
        result = run("search-keywords", "-o", str(destination), "--all", "--", *terms)
        assert result.returncode == 0 and result.stdout == b"", result.stderr
        check_result(destination.read_bytes(), "all", terms, source, order)

        for arguments in ([], ["persistence"], ["--"], ["--all", "--"],
                          ["--limit", "--", "persistence"], ["weave.xml", "--", "persistence"],
                          ["--all", "--all", "--", "persistence"], ["--", ""],
                          ["--", " \t\r\n"], ["-m", "map.json", "--", "persistence"]):
            destination.write_bytes(b"unchanged")
            result = run("-o", str(destination), "search-keywords", *arguments)
            assert result.returncode == 1 and result.stdout == b"" and result.stderr, arguments
            assert destination.read_bytes() == b"unchanged"

        for keyword in (b"\xff", b"\xe2\x82", b"\xc0\x80", b"\xe0\x80\x80",
                        b"\xf0\x80\x80\x80", b"\xed\xa0\x80", b"\xf4\x90\x80\x80",
                        b"\xe2A\x80", b"\x01", b"\x0b", "\ufffe".encode()):
            result = run("search-keywords", "--", keyword)
            assert result.returncode == 1 and result.stdout == b"" and result.stderr, keyword

        result = run("search-keywords", "-o", str(working), "--", "persistence")
        assert result.returncode == 1 and result.stdout == b""
        if Path("/dev/full").exists():
            result = run("search-keywords", "-o", "/dev/full", "--", "persistence")
            assert result.returncode == 1 and result.stderr

        cache = working / "weave.xml"
        cache_bytes = cache.read_bytes()
        # A valid fresh cache may predate keyword-index; source records suffice.
        legacy = ET.fromstring(cache_bytes)
        legacy.remove(legacy.find("keyword-index"))
        ET.ElementTree(legacy).write(cache, encoding="utf-8")
        future = time.time_ns() + 10_000_000_000
        os.utime(cache, ns=(future, future))
        search(terms)
        assert cache.stat().st_mtime_ns == future

        for invalid in (b"<wrong><articles/></wrong>", b"<lp5-weave/>",
                        b"<lp5-weave><articles/><articles/></lp5-weave>", b"<broken",
                        b'<lp5-weave xmlns="urn:wrong"><articles/></lp5-weave>'):
            cache.write_bytes(invalid)
            os.utime(cache, ns=(future, future))
            destination.write_bytes(b"unchanged")
            result = run("search-keywords", "-o", str(destination), "--", "persistence")
            assert result.returncode == 1 and result.stdout == b"" and result.stderr, invalid
            assert destination.read_bytes() == b"unchanged"
        cache.write_bytes(b"<lp5-weave><articles/></lp5-weave>")
        os.utime(cache, ns=(future, future))
        result = run("search-keywords", "--", "persistence")
        assert result.returncode == 0, result.stderr
        check_result(result.stdout, "any", ["persistence"], source, [])

        unusual_file = '</article> & "é".lp5'
        unusual = ET.Element("lp5-weave")
        article = ET.SubElement(ET.SubElement(unusual, "articles"), "article", {"file": unusual_file})
        ET.SubElement(ET.SubElement(article, "keywords"), "li").text = "literal filename"
        ET.ElementTree(unusual).write(cache, encoding="utf-8")
        os.utime(cache, ns=(future, future))
        result = run("search-keywords", "--", "literal filename")
        assert result.returncode == 0, result.stderr
        parsed = ET.fromstring(result.stdout)
        assert parsed.find("results/article").attrib == {"file": unusual_file, "score": "1"}
        assert [n.tag for n in parsed.find("results/article")] == ["matched-keywords"]

        cache.write_bytes(cache_bytes)
        os.utime(cache, ns=(future, future))
        stylesheet = working / "search-keywords.xsl"
        stylesheet.unlink()
        stylesheet.write_text('<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform" version="1.0"><xsl:template match="/"><partial/><xsl:message terminate="yes">controlled failure</xsl:message></xsl:template></xsl:stylesheet>')
        destination.write_bytes(b"unchanged")
        result = run("search-keywords", "-o", str(destination), "--", "persistence")
        assert result.returncode == 1 and result.stdout == b"" and result.stderr
        assert destination.read_bytes() == b"unchanged"
        stylesheet.unlink()
        stylesheet.symlink_to(PROJECT_DIR / "search-keywords.xsl")

        write_article(source, "4.lp5", ["new keyword"], explanation="😀" * 200)
        edited = snapshot(source)
        os.utime(cache, ns=(0, 0))
        result = search(["new keyword"])
        assert result.find("results")[0].attrib["file"] == "4.lp5"
        assert snapshot(source) == edited

        environment = dict(os.environ, LP5Source=str(source))
        result = run("search-keywords", "--", "persistence", env=environment, source_option=False)
        assert result.returncode == 0, result.stderr
        check_result(result.stdout, "any", ["persistence"], source, order)
        environment["LP5Source"] = str(working / "does-not-exist")
        result = run("search-keywords", "--", "persistence", env=environment)
        assert result.returncode == 0, result.stderr

        other = working / "other"
        other.mkdir()
        write_article(other, "lp5.lp5", ["other project"])
        result = run("search-keywords", "-s", str(other), "--", "other project", source_option=False)
        assert result.returncode == 0, result.stderr
        check_result(result.stdout, "any", ["other project"], other, ["lp5.lp5"])
        assert snapshot(source) == edited
    print("search-keywords acceptance checks passed")


if __name__ == "__main__":
    main()
