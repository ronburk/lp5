#!/usr/bin/env python3
"""Check vocabulary listing and its agreement with production keyword search."""

import os
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

from weave_keyword_index import PROJECT_DIR, write_article


def listing(result, expected, order=None):
    assert result.returncode == 0, result.stderr
    assert result.stdout.endswith(b"\n")
    root = ET.fromstring(result.stdout)
    assert root.tag == "lp5-keywords"
    assert root.attrib == {"version": "1", "total": str(len(expected))}
    actual = {}
    for keyword in root:
        assert keyword.tag == "keyword" and len(keyword) == 0
        assert set(keyword.attrib) == {"article-count"}
        assert keyword.text not in actual
        count = int(keyword.attrib["article-count"])
        assert str(count) == keyword.attrib["article-count"]
        actual[keyword.text] = count
    assert actual == expected, (actual, expected)
    if order is not None:
        assert list(actual) == order, (list(actual), order)
    return list(actual)


def main():
    if len(sys.argv) != 2:
        raise SystemExit(f"usage: {sys.argv[0]} /path/to/lp5")
    executable = str(Path(sys.argv[1]).resolve())
    with tempfile.TemporaryDirectory(prefix="lp5-list-keywords-") as temporary:
        working = Path(temporary)
        source = working / "lp5.lp5"
        source.mkdir()
        for stylesheet in ("weave.xsl", "tangle.xsl", "list-keywords.xsl", "search-keywords.xsl"):
            (working / stylesheet).symlink_to(PROJECT_DIR / stylesheet)

        special = '</keyword> & "quoted", O\'Reilly'
        write_article(source, "lp5.lp5", [" Shared ", "SAVE\t ARTICLE", "shared", " "],
                      ("2.lp5", "1.lp5"))
        write_article(source, "2.lp5", ["SHARED", "save\n\r article", "a", "z"])
        write_article(source, "1.lp5", [])
        # Orphans and Unicode remain part of the vocabulary.
        write_article(source, "a&z.lp5", [special, special, "ÉTÉ", "été", "雪", "😀",
                                          "-o", "--", "&amp;", "\u00a0", "shared"])
        expected = {"shared": 3, "save article": 2, "a": 1, "z": 1,
                    special.replace("O'Reilly", "o'reilly"): 1, "ÉtÉ": 1, "été": 1,
                    "雪": 1, "😀": 1, "-o": 1, "--": 1, "&amp;": 1, "\u00a0": 1}
        original = {p.name: p.read_bytes() for p in source.iterdir() if p.name != "weave.xml"}

        def run(*arguments, project="lp5"):
            return subprocess.run([executable, project, *arguments], cwd=working,
                                  capture_output=True)

        cache = source / "weave.xml"
        assert not cache.exists()
        order = listing(run("list-keywords"), expected)
        index = ET.parse(cache).getroot()
        assert order == [k.attrib["value"] for k in index.find("keyword-index")]
        assert [value for value in order if value in ("a", "shared", "z")] == ["a", "shared", "z"]
        for value, count in expected.items():
            result = run("search-keywords", "--", value)
            assert result.returncode == 0, result.stderr
            assert int(ET.fromstring(result.stdout).attrib["total"]) == count
        assert {p.name: p.read_bytes() for p in source.iterdir() if p.name != "weave.xml"} == original

        # No source reads or refresh when the generated cache is already current.
        timestamp = cache.stat().st_mtime_ns
        listing(run("list-keywords"), expected, order)
        assert cache.stat().st_mtime_ns == timestamp
        # Fresh caches from before keyword-index was introduced still work.
        index.remove(index.find("keyword-index"))
        ET.ElementTree(index).write(cache, encoding="utf-8")
        listing(run("list-keywords"), expected, order)
        assert ET.parse(cache).getroot().find("keyword-index") is None

        for arguments in (("extra",), ("--",), ("--all",), ("-m", "unused.map")):
            result = run("list-keywords", *arguments)
            assert result.returncode == 1 and not result.stdout and result.stderr
        for invalid in (b"<wrong/>", b"<lp5-weave/>",
                        b"<lp5-weave><articles/><articles/></lp5-weave>",
                        b'<lp5-weave xmlns="wrong"><articles/></lp5-weave>', b"<broken"):
            cache.write_bytes(invalid)
            result = run("list-keywords")
            assert result.returncode == 1 and not result.stdout and result.stderr
        cache.write_bytes(b"<lp5-weave><articles/></lp5-weave>")
        listing(run("list-keywords"), {})
        cache.write_bytes(b"<lp5-weave><articles/><keyword-index/></lp5-weave>")
        listing(run("list-keywords"), {})

        # An edit is picked up by the shared freshness mechanism.
        write_article(source, "2.lp5", ["changed keyword", "shared"])
        os.utime(cache, ns=(0, 0))
        del expected["a"], expected["z"]
        expected["save article"] = 1
        expected["changed keyword"] = 1
        listing(run("list-keywords"), expected)
        empty_source = working / "empty.lp5"
        empty_source.mkdir()
        write_article(empty_source, "empty.lp5", [" \t\n\r "])
        cache.unlink()
        listing(run("list-keywords", project="empty"), {})

    print("list-keywords acceptance checks passed")


if __name__ == "__main__":
    main()
