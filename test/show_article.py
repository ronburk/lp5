#!/usr/bin/env python3
"""Exercise source-article reading and navigation through the production CLI."""

import os
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parents[1]


def parse(data):
    return ET.fromstring(data, parser=ET.XMLParser(
        target=ET.TreeBuilder(insert_comments=True, insert_pis=True)))


def check(result, filename, original):
    assert result.returncode == 0, result.stderr
    assert result.stdout.endswith(b"\n")
    root = parse(result.stdout)
    assert root.tag == "lp5-article"
    assert root.attrib == {"version": "1", "file": filename}
    assert len(root) == 1 and root[0].tag == "template"
    assert ET.tostring(root[0]) == ET.tostring(parse(original)), result.stdout
    return root[0]


def main():
    if len(sys.argv) != 2:
        raise SystemExit(f"usage: {sys.argv[0]} /path/to/lp5")
    executable = str(Path(sys.argv[1]).resolve())
    with tempfile.TemporaryDirectory(prefix="lp5-show-article-") as temporary:
        working = Path(temporary)
        source = working / "project.lp5"
        source.mkdir()
        for stylesheet in ("show-article.xsl", "weave.xsl", "tangle.xsl", "check.xsl"):
            (working / stylesheet).symlink_to(PROJECT_DIR / stylesheet)

        root_text = b'''<template>
    <children><li id="4.lp5"/><li id="1.lp5"/><li id="missing.lp5"/></children>
    <heading>Root <em>heading</em></heading>
</template>'''
        child_text = ('''<template xmlns:meta="urn:test" meta:label="kept">
    <!-- source comment --><?test keep?>
    <heading>  A <b>marked up</b> heading &amp; more  </heading>
    <keywords><li> Mixed Case </li><li> Mixed Case </li><li> </li><li>&lt;/keyword&gt; &amp; quoted</li></keywords>
    <section data-lp5-kind="explanation"><p>First <em>second</em> tail<code>x &lt; y</code>''' + "雪😀" * 3000 + '''</p></section>
    <section data-lp5-kind="code">
        <name>Bundle <i>name</i></name>
        <code><![CDATA[  if (a < b && c > d) {
    printf("%s", "雪");
]]><lp5- ref="unresolved &amp; name"/><![CDATA[
  }
  // literal ]]]]><![CDATA[> remains code
]]></code>
    </section>
    <children/>
</template>''').encode("utf-8")
        (source / "lp5.lp5").write_bytes(root_text)
        (source / "4.lp5").write_bytes(child_text)
        (source / "1.lp5").write_bytes(b"<template><heading/><keywords/><children/></template>")
        special = 'a&amp;\'"é.lp5'
        (source / special).write_bytes(b"<template/>")
        (source / "-notes.lp5").write_bytes(b"<template><heading>Dash file</heading></template>")
        # A working-directory collision must never change project selection.
        (working / "lp5.lp5").write_bytes(b"<template><heading>wrong root</heading></template>")
        (working / "4.lp5").write_bytes(b"<template><heading>wrong article</heading></template>")
        original = {p.name: p.read_bytes() for p in source.iterdir()}

        def run(*arguments, environment=None, default_source=True):
            options = ["-s", str(source)] if default_source else []
            return subprocess.run([executable, *options, *arguments], cwd=working,
                                  env=environment, capture_output=True)

        cache = working / "weave.xml"
        assert not cache.exists()
        template = check(run("show-article"), "lp5.lp5", root_text)
        assert cache.exists()
        assert [li.attrib["id"] for li in template.find("children")] == ["4.lp5", "1.lp5", "missing.lp5"]
        result = run("show-article", "4.lp5")
        returned = check(result, "4.lp5", child_text)
        assert "// literal ]]> remains code" in "".join(returned.find("section[@data-lp5-kind='code']/code").itertext())
        assert b"<![CDATA[" in result.stdout and b'<lp5- ref="unresolved &amp; name"/>' in result.stdout
        for filename in ("lp5.lp5", "1.lp5", special, "-notes.lp5"):
            check(run("show-article", filename), filename, original[filename])
        assert {p.name: p.read_bytes() for p in source.iterdir()} == original
        cache_time = cache.stat().st_mtime_ns
        check(run("show-article", "4.lp5"), "4.lp5", child_text)
        assert cache.stat().st_mtime_ns == cache_time

        destination = working / "article.xml"
        result = run("show-article", "-o", str(destination), "4.lp5")
        assert result.returncode == 0 and not result.stdout, result.stderr
        check(subprocess.CompletedProcess([], 0, destination.read_bytes(), b""), "4.lp5", child_text)
        for arguments in (("4.lp5", "1.lp5"), ("4",), ("",), ("--all",), ("--",),
                          ("../4.lp5",), (str(source / "4.lp5"),), (r"dir\4.lp5",),
                          ("missing.lp5",), ("-m", "unused.map"), (b"\xff.lp5",), ("\x01.lp5",)):
            destination.write_bytes(b"preserve output")
            result = run("-o", str(destination), "show-article", *arguments)
            assert result.returncode == 1 and not result.stdout and result.stderr
            assert destination.read_bytes() == b"preserve output"

        # Keep the cache current to exercise direct article parse/validation errors.
        for invalid in (b"<wrong/>", b"<broken", b"<template><heading/><heading/></template>",
                        b'<template xmlns="wrong"/>', b"<template><keywords><li><b>bad</b></li></keywords></template>"):
            (source / "4.lp5").write_bytes(invalid)
            future = time.time_ns() + 10_000_000_000
            os.utime(cache, ns=(future, future))
            result = run("show-article", "4.lp5", "-o", str(destination))
            assert result.returncode == 1 and not result.stdout and result.stderr
            assert destination.read_bytes() == b"preserve output"
        changed = child_text.replace(b"Mixed Case", b"Changed Keyword")
        (source / "4.lp5").write_bytes(changed)
        os.utime(cache, ns=(0, 0))
        check(run("show-article", "4.lp5"), "4.lp5", changed)
        assert b"Changed Keyword" in cache.read_bytes()

        environment = dict(os.environ, LP5Source=str(source))
        check(run("show-article", environment=environment, default_source=False), "lp5.lp5", root_text)
        environment["LP5Source"] = str(working / "nonexistent")
        check(run("show-article", environment=environment), "lp5.lp5", root_text)
        result = run("show-article", "4.lp5", "-o", str(working))
        assert result.returncode == 1 and not result.stdout and result.stderr
        if Path("/dev/full").exists():
            result = run("show-article", "-o", "/dev/full")
            assert result.returncode == 1 and not result.stdout and result.stderr

        # Refresh failure must stop the command without replacing its destination.
        (source / "lp5.lp5").unlink()
        cache.unlink()
        result = run("show-article", "-o", str(destination))
        assert result.returncode == 1 and not result.stdout and result.stderr
        assert destination.read_bytes() == b"preserve output"

    print("show-article acceptance checks passed")


if __name__ == "__main__":
    main()
