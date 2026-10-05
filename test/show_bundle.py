#!/usr/bin/env python3
"""Check bundle vocabulary, default-index extraction, and legacy compatibility."""

import os
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parents[1]


def article(source, filename, name=None, children=()):
    root = ET.Element("template")
    if children:
        links = ET.SubElement(root, "children")
        for child in children:
            ET.SubElement(links, "li", {"id": child})
    if name is not None:
        section = ET.SubElement(root, "section", {"data-lp5-kind": "code"})
        section.append(ET.fromstring("<name>" + name + "</name>"))
        code = ET.SubElement(section, "code")
        code.text = "  literal < & code\n"
        ref = ET.SubElement(code, "lp5-", {"ref": "unresolved"})
        ref.tail = "\n  tail\n"
    ET.ElementTree(root).write(source / filename, encoding="utf-8")


def check_list(result, names):
    assert result.returncode == 0, result.stderr
    assert result.stdout.endswith(b"\n")
    root = ET.fromstring(result.stdout)
    assert root.tag == "bundles" and not root.attrib
    assert [node.attrib for node in root] == [{"name": name} for name in names]
    for node in root:
        assert node.tag == "bundle" and len(node) == 0 and not node.text


def main():
    if len(sys.argv) != 2:
        raise SystemExit(f"usage: {sys.argv[0]} /path/to/lp5")
    executable = str(Path(sys.argv[1]).resolve())
    with tempfile.TemporaryDirectory(prefix="lp5-show-bundle-") as temporary:
        working = Path(temporary)
        source = working / "source"
        source.mkdir()
        for stylesheet in ("weave.xsl", "tangle.xsl", "show-bundle.xsl"):
            (working / stylesheet).symlink_to(PROJECT_DIR / stylesheet)
        article(source, "lp5.lp5", "", ("4.lp5", "1.lp5", "2.lp5"))
        article(source, "4.lp5", " Bundle <b>&amp;</b> Names ")
        article(source, "1.lp5", "Bundle &amp; Names")
        article(source, "2.lp5")
        special = "O'Reilly & \"quotes\", 雪"
        article(source, "3.lp5", "O'Reilly &amp; &quot;quotes&quot;, 雪")
        article(source, "5.lp5", "__CODE_NAME_PARAMETER_REQUIRED__")
        article(source, "6.lp5", "weave.xml")
        article(source, "7.lp5", "-o")
        article(source, "8.lp5", "--")
        names = ["", "Bundle & Names", special, "__CODE_NAME_PARAMETER_REQUIRED__",
                 "weave.xml", "-o", "--"]
        original = {p.name: p.read_bytes() for p in source.iterdir()}

        def run(*args, environment=None, default_source=True):
            options = ["-s", str(source)] if default_source else []
            return subprocess.run([executable, *options, *args], cwd=working,
                                  env=environment, capture_output=True)

        cache = working / "weave.xml"
        assert not cache.exists()
        check_list(run("show-bundle"), names)
        timestamp = cache.stat().st_mtime_ns
        check_list(run("show-bundle"), names)
        assert cache.stat().st_mtime_ns == timestamp

        default_contents = cache.read_bytes()
        generated_alternate = working / "generated-alternate.xml"
        result = run("-w", str(generated_alternate), "show-bundle")
        check_list(result, names)
        assert generated_alternate.exists()
        assert cache.read_bytes() == default_contents

        for name in names:
            # -- allows names equal to global options without parsing them.
            result = run("show-bundle", "--", name)
            assert result.returncode == 0, result.stderr
            root = ET.fromstring(result.stdout)
            assert root.tag == "bundle" and root.attrib == {"name": name}
            assert len(root) > 0
            if name not in ("-o", "--"):
                old = run("show-bundle", "weave.xml", name)
                assert old.returncode == 0 and old.stdout == result.stdout, old.stderr
                new = run("show-bundle", name)
                assert new.returncode == 0 and new.stdout == result.stdout, new.stderr
            for section in root:
                assert section.tag == "section"
                assert section.attrib["data-lp5-kind"] == "code"
                copied = section.find("code")
                original_code = ET.parse(source / section.attrib["article"]).getroot().find("section/code")
                # Clear outside-element indentation for comparison.
                copied.tail = original_code.tail = None
                assert ET.tostring(copied) == ET.tostring(original_code)
        bundle = run("show-bundle", " Bundle\t &\nNames ")
        assert bundle.returncode == 0, bundle.stderr
        assert [s.attrib["article"] for s in ET.fromstring(bundle.stdout)] == ["4.lp5", "1.lp5"]
        missing = run("show-bundle", "not a bundle")
        assert missing.returncode == 0 and len(ET.fromstring(missing.stdout)) == 0
        # The one-argument form treats even an .xml name as a bundle name.
        xml_named = run("show-bundle", "weave.xml")
        assert xml_named.returncode == 0
        assert ET.fromstring(xml_named.stdout).attrib == {"name": "weave.xml"}
        assert len(ET.fromstring(xml_named.stdout)) > 0
        xml_named = run("show-bundle", "--", "weave.xml")
        assert xml_named.returncode == 0
        assert ET.fromstring(xml_named.stdout).attrib == {"name": "weave.xml"}
        assert {p.name: p.read_bytes() for p in source.iterdir()} == original

        output = working / "bundles.xml"
        result = run("show-bundle", "-o", str(output))
        assert result.returncode == 0 and not result.stdout, result.stderr
        check_list(subprocess.CompletedProcess([], 0, output.read_bytes(), b""), names)
        result = run("show-bundle", "Bundle & Names", "-o", str(output))
        assert result.returncode == 0 and not result.stdout, result.stderr
        assert len(ET.parse(output).getroot()) == 2

        if shutil.which("xsltproc"):
            direct = subprocess.run(["xsltproc", "show-bundle.xsl", "weave.xml"],
                                    cwd=working, capture_output=True)
            check_list(direct, names)
            direct = subprocess.run(["xsltproc", "--stringparam", "code_name", "",
                                     "show-bundle.xsl", "weave.xml"], cwd=working, capture_output=True)
            assert direct.returncode == 0 and ET.fromstring(direct.stdout).attrib == {"name": ""}

        # The legacy two-argument form still reads its explicit index file.
        alternate = working / "alternate.xml"
        alternate.write_bytes(b'<lp5-weave><articles/><bundles/></lp5-weave>')
        newest_source_mtime = max(
            source.stat().st_mtime_ns,
            *(path.stat().st_mtime_ns for path in source.iterdir()),
        )
        os.utime(alternate, ns=(newest_source_mtime + 2_000_000_000,
                                newest_source_mtime + 2_000_000_000))
        default_contents = cache.read_bytes()
        result = run("-w", str(alternate), "show-bundle", "Bundle & Names")
        assert result.returncode == 0
        assert len(ET.fromstring(result.stdout)) == 0
        assert cache.read_bytes() == default_contents

        result = run("show-bundle", str(alternate), "Bundle & Names")
        assert result.returncode == 0 and len(ET.fromstring(result.stdout)) == 0
        output.write_bytes(b"keep existing output")
        for args in (("--",), ("one", "two", "three"), ("-m", "unused.map"),
                     ("-w",)):
            result = run("show-bundle", "-o", str(output), *args)
            assert result.returncode == 1 and not result.stdout and result.stderr
            assert output.read_bytes() == b"keep existing output"
        result = run("show-bundle", "-w", "first.xml", "-w", "second.xml")
        assert result.returncode == 1 and b"specified more than once" in result.stderr
        for invalid in (b"<wrong/>", b"<lp5-weave/>",
                        b"<lp5-weave><bundles/><bundles/></lp5-weave>",
                        b'<lp5-weave xmlns="wrong"><bundles/></lp5-weave>', b"<broken"):
            cache.write_bytes(invalid)
            result = run("show-bundle", "-o", str(output))
            assert result.returncode == 1 and not result.stdout and result.stderr
            assert output.read_bytes() == b"keep existing output"
        cache.write_bytes(b"<lp5-weave><articles/><bundles/></lp5-weave>")
        check_list(run("show-bundle"), [])

        article(source, "1.lp5", "Changed")
        os.utime(cache, ns=(0, 0))
        names.insert(2, "Changed")
        check_list(run("show-bundle"), names)
        environment = dict(os.environ, LP5Source=str(source))
        check_list(run("show-bundle", environment=environment, default_source=False), names)
        environment["LP5Source"] = str(working / "nonexistent")
        check_list(run("show-bundle", environment=environment), names)
        result = run("show-bundle", "-o", str(working))
        assert result.returncode == 1 and not result.stdout and result.stderr
        if Path("/dev/full").exists():
            result = run("show-bundle", "-o", "/dev/full")
            assert result.returncode == 1 and not result.stdout and result.stderr
    print("show-bundle acceptance checks passed")


if __name__ == "__main__":
    main()
