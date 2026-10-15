#!/usr/bin/env python3
"""Return source fixtures and actual harness output for browser comparison."""
import json
import shutil
import subprocess
import tempfile
from html import escape
from pathlib import Path


def fixture():
    repo = Path(__file__).resolve().parents[1]
    literal = lambda text: "<![CDATA[" + text + "]]>"
    ref = lambda name: '<lp5- ref="' + name + '"/>'

    def article(title, name, code, children=()):
        return '<template><heading>' + title + '</heading>' + (
            '<children>' + ''.join('<li id="' + child + '"/>' for child in children) + '</children>'
            if children else '') + '<section data-lp5-kind="code"><name>' + escape(name) + \
            '</name><code>' + code + '</code></section></template>'

    leaf = "leaf &amp; <script>window.outputExecuted = true;</script>\n" + \
        ''.join(f"line {i}\n" for i in range(60))
    files = {
        "fixture.lp5": article("Root", "", literal("head &amp; <tag>\n  before ") + ref("Shared") +
            literal(" after\n") + ref("Shared") + literal("\n") +
            '<lp5-wrapper attr="a&amp;b">' + ref("Leaf") + '</lp5-wrapper>' + literal("\ntail\n"),
            ["1.lp5", "2.lp5", "3.lp5", "4.lp5", "5.lp5"]),
        "1.lp5": article("Shared first", "Shared", literal("A[") + ref("Leaf") + literal("]\n")),
        "2.lp5": article("Shared second", "Shared", literal("B\n")),
        "3.lp5": article("Leaf", "Leaf", literal(leaf)),
        "4.lp5": article("Other output", "<other.js>", literal("other:") + ref("Shared")),
        "5.lp5": article("Unused", "Unused", literal("unused:") + ref("Leaf")),
    }
    with tempfile.TemporaryDirectory(prefix="lp5-output-") as directory:
        for stylesheet in ("weave.xsl", "tangle.xsl"):
            shutil.copy2(repo / stylesheet, Path(directory) / stylesheet)
        source = Path(directory) / "fixture.lp5"
        source.mkdir()
        for name, text in files.items():
            (source / name).write_text(text)
        subprocess.run([str(repo / "lp5"), "fixture", "tangle"], cwd=directory,
                       check=True, capture_output=True)
        expected = {"": (source / "fixture.out").read_text(),
                    "<other.js>": (source / "other.js").read_text()}
    return {"files": files, "expected": expected}


if __name__ == "__main__":
    print(json.dumps(fixture()))
